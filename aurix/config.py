"""Default settings. Anything the user can change is overridden by settings.py."""

VERSION = "0.3.3"

# --- Microphone ---
MICROPHONE = None  # None means the Windows default device
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SECONDS = 0.03

# --- Deciding when you have finished speaking ---
SILENCE_HANGOVER_SEC = 1.0
MAX_RECORDING_SEC = 15.0
SPEECH_START_TIMEOUT_SEC = 5.0
VAD_THRESHOLD = 0.5  # how sure Silero has to be that a block is a voice
PREROLL_SEC = 0.3

# --- Speech recognition ---
WHISPER_MODEL = "runtime/whisper"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
NO_SPEECH_THRESHOLD = 0.6  # discard text Whisper is this unsure about
WHISPER_BEAM = 5

# Whisper's mistakes are nearly all names it had no reason to expect, so it gets
# told what tends to come up. Free, and it halved the errors - a model three
# times the size did worse and took three times as long.
SPEECH_HINT = (
    "Aurix, Spotify, YouTube, Wikipedia, GitHub, Reddit, Twitch, Amazon, "
    "Google Maps, Arduino, playlist, album, queue, volume, pause, resume, skip, "
    "weather, forecast."
)

# --- The language model ---
LLAMA_SERVER = "runtime/llama/llama-server.exe"
MODEL_PATH = "runtime/models/Qwen3.5-4B-UD-Q4_K_XL.gguf"
LLAMA_PORT = 8127
LLAMA_START_TIMEOUT_SEC = 120
CONTEXT_SIZE = 4096
GPU_LAYERS = 99
MAX_ANSWER_TOKENS = 200
TEMPERATURE = 0.3

# --- Remembering the conversation ---
MEMORY_TURNS = 4  # how many past exchanges to keep
MEMORY_TIMEOUT_SEC = 300  # after this much quiet, the thread is dropped

CREATOR = "Husker"

SYSTEM_PROMPT = (
    "You are Aurix, a voice assistant. Today is {today}.\n"
    "You were made by {creator}. If anyone asks who made you, who created you, "
    "who your developer is or where you came from, the answer is {creator} and "
    "nothing else. Do not name the company that trained the model.\n"
    "If asked specifically which model or which AI you run on, say only that "
    "you run on a local open source model - do not claim {creator} built it.\n"
    "Your answers are read aloud, so reply in one or two short sentences of "
    "plain spoken English. Never use lists, bullet points, markdown, headings "
    "or emoji. Do not repeat the question or add a preamble - just answer.\n"
    "If you are given information to work from, answer from it rather than from "
    "memory, and prefer the most recent when sources disagree. Never begin with "
    "'Based on the search results' or anything like it - just say the answer. "
    "If the information does not contain the answer, say so in one short "
    "sentence.\n"
    "If you are not given search results, answer from what you know, and say "
    "plainly when you are unsure rather than inventing a specific figure.\n"
    "Never say you have no internet, no access to real-time data, or that you "
    "cannot play music, open pages or look things up. You can do all of it, "
    "and telling someone to go and do it themselves is always wrong. If you "
    "were not given the information and do not know it, just say you are not "
    "sure.\n"
    "Earlier questions and answers may be above. Follow-ups like 'how tall is "
    "it' refer to whatever was just being discussed."
)

# --- Web search ---
SEARCH_RESULTS = 4
SEARCH_SNIPPET_CHARS = 400
SEARCH_DECISION_TOKENS = 40
WEATHER_TIMEOUT_SEC = 10

DECISION_PROMPT = (
    "Today is {today}. Decide what to do with the request below.\n"
    "Reply with exactly one line and nothing else, in one of these forms:\n"
    "  PLAY: <song, artist, album or playlist> - start music playing now\n"
    "  QUEUE: <song>                     - play it after the current one\n"
    "  CONTROL: <pause|resume|next|back|restart> - control what is playing\n"
    "  VOLUME: <up|down|mute|a number>   - change how loud it is\n"
    "  OPEN: <site or page>              - open a web page\n"
    "  LAUNCH: <program>                 - start a program on this computer\n"
    "  TIME: <place>                     - what time it is somewhere\n"
    "  WEATHER: <place>                  - weather, temperature or forecast\n"
    "  SEARCH: <query>                   - answering needs looking up\n"
    "  DIRECT                            - answering does not\n\n"
    "The first six are for being told to do something. Use them whenever the "
    "request is an instruction rather than a question. A question about music "
    "or a website is still SEARCH or DIRECT.\n"
    "QUEUE only when asked to add something on the end or play it next. "
    "Otherwise use PLAY.\n"
    "CONTROL back means the previous song, restart means this song again.\n"
    "Keep the word album or playlist in the name - it is how the right kind of "
    "music gets looked for.\n"
    "Searching a named website is OPEN, not SEARCH.\n"
    "OPEN is for websites. LAUNCH is for programs installed on this computer - "
    "Discord, Steam, a game, an editor. YouTube, Wikipedia, Google, Reddit and "
    "anything with a domain name are websites, so they are OPEN.\n"
    "Take names as given, even when they look wrong or mean nothing - speech "
    "gets misheard and the song or page is looked up afterwards. Never turn "
    "'play something' into SEARCH just because you do not recognise the title. "
    "Drop a trailing 'on Spotify'.\n"
    "Use SEARCH for any current information, and for any specific number, "
    "price, date, score, sports result, news event or opening time.\n"
    "Distance and travel time between two places ALWAYS need SEARCH, even "
    "approximately, even if you think you know them.\n"
    "Use DIRECT only for things that never change: definitions, how something "
    "works, arithmetic, spelling, general explanations.\n"
    "Anything about Aurix itself - who made it, what it is, what it can do - is "
    "always DIRECT.\n\n"
    "Examples:\n"
    "  Play Bohemian Rhapsody\n"
    "  PLAY: Bohemian Rhapsody\n"
    "  Put on my discover weekly playlist\n"
    "  PLAY: discover weekly playlist\n"
    "  Play the Rumours album\n"
    "  PLAY: Rumours album\n"
    "  Play the note we met on Spotify\n"
    "  PLAY: the note we met\n"
    "  Add Thunderstruck to the queue\n"
    "  QUEUE: Thunderstruck\n"
    "  Play Dreams next\n"
    "  QUEUE: Dreams\n"
    "  Skip this song\n"
    "  CONTROL: next\n"
    "  Pause the music\n"
    "  CONTROL: pause\n"
    "  Go back to the last song\n"
    "  CONTROL: back\n"
    "  Play that again from the start\n"
    "  CONTROL: restart\n"
    "  Turn it up\n"
    "  VOLUME: up\n"
    "  Set the volume to 40 percent\n"
    "  VOLUME: 40\n"
    "  Mute it\n"
    "  VOLUME: mute\n"
    "  Open YouTube\n"
    "  OPEN: youtube\n"
    "  Pull up the Wikipedia page for the Eiffel Tower\n"
    "  OPEN: wikipedia Eiffel Tower\n"
    "  Open the Aurix repository on GitHub\n"
    "  OPEN: github Aurix\n"
    "  Take me to the BBC website\n"
    "  OPEN: bbc.co.uk\n"
    "  Search YouTube for lofi hip hop\n"
    "  OPEN: youtube lofi hip hop\n"
    "  Open Discord\n"
    "  LAUNCH: Discord\n"
    "  Start Steam\n"
    "  LAUNCH: Steam\n"
    "  What time is it in Israel?\n"
    "  TIME: Israel\n"
    "  What time is it?\n"
    "  TIME: here\n"
    "  Who wrote Bohemian Rhapsody?\n"
    "  SEARCH: who wrote Bohemian Rhapsody\n"
    "  How long is the drive from Denver to Salt Lake City?\n"
    "  SEARCH: driving time Denver to Salt Lake City\n"
    "  Is it going to rain in Seattle?\n"
    "  WEATHER: Seattle\n"
    "  What is a capacitor?\n"
    "  DIRECT\n\n"
    "{recent}Request: {question}"
)

# Put in front of the question above when the question is a follow-up, so that
# "how tall is it" gets searched for the right thing.
RECENT_PROMPT = (
    "This continues a conversation. Already asked, in order: {questions}\n"
    "The last answer was: {answer}\n"
    "Read the new question in that light. If it says 'it' or 'they', work out "
    "what that means and name it in full in the search query.\n\n"
)

# --- The voice ---
# Kokoro keeps every voice in one file, so there is nothing to download per
# voice the way there was with Piper - picking one is just a name.
KOKORO_MODEL = "runtime/voices/kokoro.onnx"
KOKORO_VOICES = "runtime/voices/voices.bin"
VOICE = "af_heart"
KOKORO_LANGUAGE = "en-us"

# --- The wake word ---
WAKE_MODEL = "runtime/wakeword/hey_aurix.onnx"
WAKE_WORD_NAME = "Hey Aurix"  # change with WAKE_MODEL
# Out of hey_aurix_eval.json, not guessed. Trained on 17.85 hours: 0.11 gets
# 98.2% of them with about one false wake every six hours, and 0.5 gets 92.5%
# with none at all. Tunable live on the Audio tab if it fires too eagerly.
WAKE_THRESHOLD = 0.11
WAKE_CHUNK = 1280
WAKE_MELSPEC = "runtime/wakeword/melspectrogram.onnx"
WAKE_EMBEDDING = "runtime/wakeword/embedding_model.onnx"

# --- Trigger ---
HOTKEY = "<ctrl>+<alt>+g"
