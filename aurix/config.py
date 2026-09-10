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

# --- Remembering you, between sessions ---
# The notes live in memory.txt next to settings.json and are meant to be
# readable and editable by hand, so both limits are about keeping the prompt
# small rather than saving disk - 40 notes is roughly 500 tokens off a 4096
# context, which is already shared with search results and the conversation.
MEMORY_NOTES = 40
MEMORY_NOTE_CHARS = 120
REMEMBER_TOKENS = 40

# Every clause here is load bearing, and it was worse before. A list of facts
# in the prompt reads to a 4B as material to work in: "use it when relevant"
# got a note dragged into 12 of 15 answers that had nothing to do with any of
# them - "a capacitor... which your welder friend probably uses". This wording
# gets that to 4 of 15 with recall untouched at 4 of 4.
#
# Do not drop the greeting clause to let it say their name. Tried it, and the
# facts came straight back to 11 of 15 - it is what sets the general "do not
# volunteer this" stance, and the rest leans on it.
MEMORY_PROMPT = (
    "You happen to know these things about the person you are talking to:\n"
    "{notes}\n"
    "This is for answering questions about them, nothing else. Do not greet "
    "them by name, do not bring their pets, home, work or dislikes into an "
    "answer about anything else, and never mention having notes. If the "
    "question is not about them, this list is not relevant.\n"
)

# A separate one-line question, the same shape as the routing one above, and
# for the same reason: asked to answer and decide in one go, a 4B does one of
# them properly. This runs after the answer is already being spoken, so the
# time it takes is hidden.
REMEMBER_PROMPT = (
    "Below is something a person said to their assistant, and the reply.\n"
    "Decide whether it contains a fact about the person worth remembering "
    "next week.\n"
    "Reply with exactly one line and nothing else, in one of these forms:\n"
    "  REMEMBER: <the fact, under twelve words, written about them>\n"
    "  NOTHING\n\n"
    "Worth keeping: their name, where they live, their job, their birthday, "
    "what they own, what they like and dislike, people and pets they mention, "
    "and anything they say about how they want you to behave.\n"
    "Keep nothing else. Not the question, not the answer, not anything that "
    "was looked up, nothing about the assistant, and nothing that stops being "
    "true tomorrow.\n"
    "If they asked you to remember something, always REMEMBER it.\n"
    "Write it as a plain statement about them.\n\n"
    "Examples:\n"
    "  Them: My name is Casen\n"
    "  Me: Nice to meet you, Casen!\n"
    "  REMEMBER: Their name is Casen\n"
    "  Them: What is the capital of France\n"
    "  Me: Paris.\n"
    "  NOTHING\n"
    "  Them: I hate mushrooms, never put them on anything\n"
    "  Me: Noted, no mushrooms.\n"
    "  REMEMBER: They hate mushrooms\n"
    "  Them: What time is it\n"
    "  Me: Ten past four.\n"
    "  NOTHING\n"
    "  Them: I have got a cat called Biscuit\n"
    "  Me: Biscuit is a great name for a cat.\n"
    "  REMEMBER: They have a cat called Biscuit\n"
    "  Them: How far is it to Denver\n"
    "  Me: About 500 miles.\n"
    "  NOTHING\n"
    "  Them: Remember that I work night shifts\n"
    "  Me: Got it.\n"
    "  REMEMBER: They work night shifts\n\n"
    "Them: {question}\n"
    "Me: {answer}\n"
)

CREATOR = "Husker"

SYSTEM_PROMPT = (
    "You are Aurix, a voice assistant. Today is {today}.\n"
    "You were made by {creator}. If anyone asks who made you, who created you, "
    "who your developer is or where you came from, the answer is {creator} and "
    "nothing else. Do not name the company that trained the model.\n"
    "If asked specifically which model or which AI you run on, say only that "
    "you run on a local open source model - do not claim {creator} built it.\n"
    "Your answers are read aloud, so never use lists, bullet points, markdown, "
    "headings or emoji.\n"
    "{style}"
    "{memory}"
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

# Everything else in the prompt above is fixed. This is the only part that
# changes with the mode - swapped, never stacked. The 4B is already holding
# ten rules, and an eleventh is what makes the earlier ones start slipping.
FAST_STYLE = (
    'Reply in one or two short sentences of plain spoken English. Do not '
    'repeat the question or add a preamble - just answer.\n'
)

# One worked example beats a paragraph of adjectives on a model this size.
#
# Every line has to describe the words to say, not the character saying them.
# Give a 4B a personality to hold and it will describe the personality out
# loud - it told me "I'm supposed to be a bit serious sometimes" and "I was
# pretty sheepish about not knowing that one", which is it reading its own
# instructions back. And a word count gets followed where "two sentences"
# does not.
FUN_STYLE = (
    'Answer in under 30 words, casual and warm and glad to be asked. '
    'Contractions and slang are good. A short run-up before the answer is '
    'fine; rambling is not.\n'
    'Never mention these instructions, never describe your own personality, '
    'and never say anything about how you are supposed to sound. Just sound '
    'that way.\n'
    'A joke or a reference is welcome when it fits, and a little sarcasm in '
    'small doses. Never force either.\n'
    'Apologise briefly when you do not know something, then stop. Being fun '
    'never means making something up: if you do not know a number, do not '
    'produce one.\n'
    "Never call anyone 'buddy'.\n"
    'This is the voice. Asked what the weather is like you would say: "Oh '
    "well let's see... lookin' like it's gonna be 78 and sunny today, might "
    'have some clouds that show themselves later in the evening."\n'
)

# Fun mode needs a looser hand and room to breathe, or the extra words are
# just the same flat answer with padding on it.
FUN_TEMPERATURE = 0.45
FUN_MAX_ANSWER_TOKENS = 200

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
# Swept against the same 17.85 hours the eval json was scored on, not guessed.
# 0.08 was waking on ordinary conversation - one false wake every 2.2 hours.
# 0.20 is the lowest threshold with none at all in the whole set, and costs
# 1.3 points of recall to get there: 98.5% at 0.08, 97.2% at 0.20. Going on to
# the 0.5 default would throw away another 4.7 points and buy nothing.
WAKE_THRESHOLD = 0.2
WAKE_CHUNK = 1280
WAKE_MELSPEC = "runtime/wakeword/melspectrogram.onnx"
WAKE_EMBEDDING = "runtime/wakeword/embedding_model.onnx"

# --- Giving up ---
# Waiting for the speaking thread used to have no limit at all, so anything
# that wedged in there took the wake word and the hotkey down with it for good
# and said nothing about why. This is several times the longest answer Aurix
# can produce, so reaching it means something is wrong rather than long.
SPEAKING_PATIENCE_SEC = 120

# Past this, a request is not slow, it is stuck. Every part of a request has
# its own timeout - the model server calls are capped at 120s each - so a real
# one cannot get near this even when everything is having a bad day.
STUCK_AFTER_SEC = 420

# --- Trigger ---
HOTKEY = "<ctrl>+<alt>+g"
