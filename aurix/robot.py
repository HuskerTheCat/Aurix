"""Turning a plain spoken line into Aurix's own voice.

A vocoder is what does the work. It takes the shape of the spoken audio and
plays it through a synthetic tone instead of a human voice, which is why robots
sound like robots - the pitch stops being a person's and becomes a fixed buzz.
Everything after it is texture: a chorus for the doubled synthetic feel, a
little ring modulation for grit, and a short comb delay for the metallic edge.

The one thing that is not obvious: s and x and sh are not made by the voice at
all, they are hiss. Pushed through a tone they come out as a buzz on the end of
every word, which is the single thing that most gives the trick away. So each
moment is measured for how noise-like it is, and the hissy ones are played
through noise instead. See `_breathiness`.

All numpy, so it costs nothing to ship and works on whatever makes the audio.
Measured at about 36 ms for six seconds of speech, against roughly 1.6 seconds
to synthesise that same speech - call it two percent.
"""

import numpy as np

# Aurix speaks a little above the voice it is built from. The engine is asked
# for speech this much slower and it gets played back this much faster, so the
# pitch goes up and the length does not change - which matters, because the
# face moves along a timer against how long the audio is.
PITCH = 1.09
SPEAK_SPEED = 1.0 / PITCH

# How the voice is put together. These came out of listening to a lot of takes,
# not out of theory, so they are the sound rather than a starting point.
CARRIER_HZ = 165.0  # the robot's own tone, nothing to do with the voice's pitch
VOCODER = 0.72      # how much of it is machine and how much is still the voice
CHORUS = 0.22
RING_HZ = 45.0
RING = 0.18
COMB_MS = 4.0
COMB = 0.16

# Telling hiss from voice. Above this share of energy over SPLIT_HZ, a moment is
# treated as breath rather than voice and gets played through noise.
SPLIT_HZ = 3000.0
BREATH_FLOOR = 0.12
BREATH_SPAN = 0.20

_WINDOW = 1024
_HOP = 256


def apply(audio: np.ndarray, rate: int) -> np.ndarray:
    """Make a plain spoken line sound like Aurix. Float in, float out.

    The audio must have been asked for at SPEAK_SPEED, or it comes out the
    wrong length and slow.
    """
    voice = _faster(audio, PITCH)
    out = _vocode(voice, rate)
    out = _chorus(out, rate)
    out = _ring(out, rate)
    out = _comb(out, rate)
    return _as_loud_as(out, voice)


def _faster(audio: np.ndarray, ratio: float) -> np.ndarray:
    """Play it faster, which raises the pitch. Slow speech in, normal speed out."""
    return np.interp(
        np.arange(0, len(audio), ratio), np.arange(len(audio)), audio
    )


# --- the machine in the voice ---


def _vocode(audio: np.ndarray, rate: int) -> np.ndarray:
    """Play the shape of the speech through a tone instead of a person."""
    spoken = _analyse(audio)
    tone = _analyse(_sawtooth(len(audio), rate, CARRIER_HZ))

    frames = min(len(spoken), len(tone))
    spoken, tone = spoken[:frames], tone[:frames]
    loudness = np.abs(spoken)

    carrier = _carrier(tone, _breathiness(loudness, rate))
    rebuilt = _rebuild(loudness * carrier, len(audio))
    return (1 - VOCODER) * audio + VOCODER * rebuilt


def _carrier(tone: np.ndarray, breath: np.ndarray) -> np.ndarray:
    """The tone to speak through, swapped for noise wherever it is hiss."""
    steady = tone / np.maximum(np.abs(tone), 1e-8)
    hiss = np.exp(1j * np.random.default_rng(7).uniform(0, 2 * np.pi, tone.shape))

    mixed = (1 - breath[:, None]) * steady + breath[:, None] * hiss
    return mixed / np.maximum(np.abs(mixed), 1e-8)


def _breathiness(loudness: np.ndarray, rate: int) -> np.ndarray:
    """How much each moment is hiss rather than voice, from 0 to 1.

    Two clues, and either is enough. Hiss puts most of its energy high up, and
    hiss is flat across the spectrum where a voice has peaks where the harmonics
    are. Measured on real speech, vowels sat at 0.02 to 0.12 of their energy
    above 3 kHz and the s in "ask" jumped to 0.88, which is what makes this
    work at all.
    """
    frequencies = np.fft.rfftfreq(_WINDOW, 1 / rate)
    total = np.maximum(loudness.sum(axis=1), 1e-8)
    high = loudness[:, frequencies > SPLIT_HZ].sum(axis=1) / total

    positive = np.maximum(loudness, 1e-10)
    flatness = np.exp(np.mean(np.log(positive), axis=1)) / np.mean(positive, axis=1)

    breath = np.maximum(
        np.clip((high - BREATH_FLOOR) / BREATH_SPAN, 0, 1),
        np.clip((flatness - 0.30) / 0.25, 0, 1),
    )
    # smoothed, or it flickers between the two within a single sound
    return np.convolve(breath, [0.25, 0.5, 0.25], mode="same")


def _sawtooth(length: int, rate: int, hertz: float) -> np.ndarray:
    """A buzz with plenty of harmonics for the speech to be shaped onto."""
    turns = np.arange(length) / rate * hertz
    return 2 * (turns - np.floor(0.5 + turns))


# --- texture on top ---


def _chorus(audio: np.ndarray, rate: int) -> np.ndarray:
    """A wandering copy just behind, for the doubled synthetic feel."""
    count = len(audio)
    wander = np.sin(2 * np.pi * 1.2 * np.arange(count) / rate)
    behind = (18.0 + 2.5 * wander) * rate / 1000.0
    delayed = np.interp(
        np.clip(np.arange(count) - behind, 0, count - 1), np.arange(count), audio
    )
    return (1 - CHORUS) * audio + CHORUS * delayed


def _ring(audio: np.ndarray, rate: int) -> np.ndarray:
    """Multiply by a low tone. A little of this reads as electrical."""
    hum = np.sin(2 * np.pi * RING_HZ * np.arange(len(audio)) / rate)
    return (1 - RING) * audio + RING * (audio * hum)


def _comb(audio: np.ndarray, rate: int) -> np.ndarray:
    """A copy a few milliseconds behind. Too short to hear as an echo, it
    cancels and reinforces its way into a metallic ring instead."""
    behind = int(COMB_MS * rate / 1000)
    delayed = np.concatenate([np.zeros(behind), audio[:-behind]])
    return (1 - COMB) * audio + COMB * delayed


# --- keeping the level ---


def _as_loud_as(audio: np.ndarray, before: np.ndarray) -> np.ndarray:
    """Match the level it had before, so answers do not come out quiet.

    The vocoder leaves a few sharp peaks and a much quieter body, so matching
    peaks would make it far too quiet. Averages are matched instead and the
    peaks that then stick out are rounded off rather than clipped.
    """
    wanted = float(np.sqrt(np.mean(np.square(before))))
    have = float(np.sqrt(np.mean(np.square(audio))))
    levelled = audio * (wanted / max(have, 1e-8))

    peak = float(np.abs(levelled).max())
    if peak <= 0.95:
        return levelled
    return np.tanh(levelled / peak * 1.4) * 0.95


# --- into and out of the frequency domain ---


def _analyse(audio: np.ndarray) -> np.ndarray:
    """Chop into overlapping frames and take each one's spectrum."""
    window = np.hanning(_WINDOW)
    frames = 1 + max(0, (len(audio) - _WINDOW) // _HOP)
    return np.array([
        np.fft.rfft(audio[at * _HOP : at * _HOP + _WINDOW] * window)
        for at in range(frames)
    ])


def _rebuild(spectra: np.ndarray, length: int) -> np.ndarray:
    """Back to a waveform, overlapping the frames and undoing the window."""
    window = np.hanning(_WINDOW)
    out = np.zeros((len(spectra) - 1) * _HOP + _WINDOW)
    weight = np.zeros_like(out)

    for at, spectrum in enumerate(spectra):
        piece = slice(at * _HOP, at * _HOP + _WINDOW)
        out[piece] += np.fft.irfft(spectrum, _WINDOW) * window
        weight[piece] += window ** 2

    out /= np.maximum(weight, 1e-8)
    return np.pad(out, (0, max(0, length - len(out))))[:length]
