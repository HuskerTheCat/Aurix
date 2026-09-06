"""Every tunable setting for Gab lives here."""

# --- Microphone ---
# Which microphone to listen to. None uses the Windows default device.
# Otherwise any part of the device name, for example "HyperX Quadcast".
MICROPHONE = "HyperX Quadcast"

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SECONDS = 0.03  # how often we check the microphone level

# --- Deciding when you have finished speaking ---
# Quiet time that ends a recording. Measured against real speech: a natural
# mid-sentence pause ran just under 0.8s, so 1.0s clears it with a little room.
# 1.5s was tried and felt sluggish in use. Proper voice-activity detection,
# which can tell a thinking pause from a finished sentence, replaces this
# guesswork when the wake word lands.
SILENCE_HANGOVER_SEC = 1.0
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

# --- The language model ---
# llama.cpp's Vulkan build, which uses whatever graphics card is present -
# AMD, Intel or NVIDIA - and the processor when there is no usable card.
LLAMA_SERVER = "runtime/llama/llama-server.exe"
MODEL_PATH = "runtime/models/Qwen3.5-4B-UD-Q4_K_XL.gguf"
LLAMA_PORT = 8127
LLAMA_START_TIMEOUT_SEC = 120
CONTEXT_SIZE = 4096
GPU_LAYERS = 99  # offload everything that fits; llama.cpp keeps the rest on CPU
MAX_ANSWER_TOKENS = 200
TEMPERATURE = 0.7

# Spoken answers, so no lists and no markdown. Short, because every extra
# sentence is extra seconds of someone waiting to hear the end of it.
SYSTEM_PROMPT = (
    "You are Gab, a voice assistant. Your answers are read aloud, so reply in "
    "one or two short sentences of plain spoken English. Never use lists, "
    "bullet points, markdown, headings or emoji. Do not repeat the question or "
    "add a preamble - just answer. If you do not know something, say so in one "
    "short sentence rather than guessing."
)

# --- Trigger ---
# Temporary. The "Hey Gab" wake word replaces this once the audio path is proven.
HOTKEY = "<ctrl>+<alt>+g"
