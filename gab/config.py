"""Every tunable setting for Gab lives here."""

# --- Microphone ---
# Which microphone to listen to. None uses the Windows default device.
# Otherwise any part of the device name, for example "HyperX Quadcast".
MICROPHONE = None

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SECONDS = 0.03  # how often we check the microphone level

# --- Deciding when you have finished speaking ---
SILENCE_HANGOVER_SEC = 0.8  # quiet time that ends a recording
MAX_RECORDING_SEC = 15.0  # hard stop, so it can never run away
SPEECH_START_TIMEOUT_SEC = 5.0  # give up if nobody says anything
NOISE_CALIBRATION_SEC = 0.4  # listen to the room first
SPEECH_THRESHOLD_MULTIPLIER = 3.0  # how much louder than the room counts as speech
MIN_SPEECH_LEVEL = 0.004  # floor, so a silent room does not trigger on nothing
PREROLL_SEC = 0.3  # audio kept from before speech started, so no clipped first word

# --- Speech recognition ---
WHISPER_MODEL = "base.en"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
# Whisper invents words when it hears silence. Anything it is this unsure
# about is thrown away.
NO_SPEECH_THRESHOLD = 0.6

# --- Trigger ---
# Temporary. The "Hey Gab" wake word replaces this once the audio path is proven.
HOTKEY = "<ctrl>+<alt>+g"
