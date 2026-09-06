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
# Low, deliberately. A chattier setting makes it confidently invent facts
# rather than looking them up.
TEMPERATURE = 0.3

# Spoken answers, so no lists and no markdown. Short, because every extra
# sentence is extra seconds of someone waiting to hear the end of it.
# {today} is filled in at runtime - a model has no idea what day it is.
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

# Deciding whether to search is a separate, deliberately tiny question. Asked
# as part of answering, a 4B model only volunteers a search about half the
# time - it will happily announce that it needs to look something up and then
# not do it. Asked on its own, with one of two possible replies, it is
# reliable. Costs about a tenth of a second.
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
# Placeholder. None of the Piper voices were especially liked; this one was
# the least bad of the five tried. Being a high-quality model it takes about
# a second to generate an answer's worth of speech, against a quarter of a
# second for the medium ones - worth revisiting along with the voice itself.
VOICE_MODEL = "runtime/voices/en_GB-cori-high.onnx"

# --- Trigger ---
# Temporary. The "Hey Gab" wake word replaces this once the audio path is proven.
HOTKEY = "<ctrl>+<alt>+g"
