"""Default settings. Anything the user can change is overridden by settings.py."""

# --- Microphone ---
MICROPHONE = None  # None means the Windows default device
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SECONDS = 0.03

# --- Deciding when you have finished speaking ---
SILENCE_HANGOVER_SEC = 1.0
MAX_RECORDING_SEC = 15.0
SPEECH_START_TIMEOUT_SEC = 5.0
NOISE_CALIBRATION_SEC = 0.4
SPEECH_THRESHOLD_MULTIPLIER = 3.0
MIN_SPEECH_LEVEL = 0.004
PREROLL_SEC = 0.3

# --- Speech recognition ---
WHISPER_MODEL = "runtime/whisper"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
NO_SPEECH_THRESHOLD = 0.6  # discard text Whisper is this unsure about

# --- The language model ---
LLAMA_SERVER = "runtime/llama/llama-server.exe"
MODEL_PATH = "runtime/models/Qwen3.5-4B-UD-Q4_K_XL.gguf"
LLAMA_PORT = 8127
LLAMA_START_TIMEOUT_SEC = 120
CONTEXT_SIZE = 4096
GPU_LAYERS = 99
MAX_ANSWER_TOKENS = 200
TEMPERATURE = 0.3

SYSTEM_PROMPT = (
    "You are Gab, a voice assistant. Today is {today}.\n"
    "Your answers are read aloud, so reply in one or two short sentences of "
    "plain spoken English. Never use lists, bullet points, markdown, headings "
    "or emoji. Do not repeat the question or add a preamble - just answer.\n"
    "If you are given information to work from, answer from it rather than from "
    "memory, and prefer the most recent when sources disagree. Never begin with "
    "'Based on the search results' or anything like it - just say the answer. "
    "If the information does not contain the answer, say so in one short "
    "sentence.\n"
    "If you are not given search results, answer from what you know, and say "
    "plainly when you are unsure rather than inventing a specific figure."
)

# --- Web search ---
SEARCH_RESULTS = 4
SEARCH_SNIPPET_CHARS = 400
SEARCH_DECISION_TOKENS = 40
WEATHER_TIMEOUT_SEC = 10

DECISION_PROMPT = (
    "Today is {today}. Decide how to answer the question below.\n"
    "Reply with exactly one line and nothing else, in one of these three forms:\n"
    "  WEATHER: <place>   - for anything about weather, temperature or forecast\n"
    "  SEARCH: <query>    - when the answer needs looking up\n"
    "  DIRECT             - when it does not\n\n"
    "Use SEARCH for any current information, and for any specific number, "
    "price, date, score, sports result, news event or opening time.\n"
    "Distance and travel time between two places ALWAYS need SEARCH, even "
    "approximately, even if you think you know them.\n"
    "Use DIRECT only for things that never change: definitions, how something "
    "works, arithmetic, spelling, general explanations.\n\n"
    "Examples:\n"
    "  How long is the drive from Denver to Salt Lake City?\n"
    "  SEARCH: driving time Denver to Salt Lake City\n"
    "  Is it going to rain in Seattle?\n"
    "  WEATHER: Seattle\n"
    "  What is a capacitor?\n"
    "  DIRECT\n\n"
    "Question: {question}"
)

# --- The voice ---
VOICE_MODEL = "runtime/voices/en_GB-cori-high.onnx"

# --- The wake word ---
WAKE_MODEL = "runtime/wakeword/hey_jarvis_v0.1.onnx"
WAKE_WORD_NAME = "Hey Jarvis"  # change with WAKE_MODEL
WAKE_THRESHOLD = 0.5
WAKE_CHUNK = 1280
WAKE_MELSPEC = "runtime/wakeword/melspectrogram.onnx"
WAKE_EMBEDDING = "runtime/wakeword/embedding_model.onnx"

# --- Trigger ---
HOTKEY = "<ctrl>+<alt>+g"
