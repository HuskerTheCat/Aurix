# What is left

Roughly in the order worth doing.

## Next

**1. Doing things, not just answering.** Opening apps, opening web pages,
playing a song. This was in the original scope and never got built.
`brain._route()` answers with `direct`, `search` or `weather` today - new verbs
go there.

**2. Knowing when you have stopped talking.** A fixed one-second timer ends a
recording. Measured against real speech, a natural mid-sentence pause ran just
under 0.8s, so this clears it by very little and a slower talker gets cut off.
Voice-activity detection can tell a thinking pause from a finished sentence and
would be safer *and* faster. Silero is already on disk in `runtime/wakeword/`.

This also fixes the room measurement: background noise is sampled once at
startup, so a noise at that moment sets a bad threshold for the whole session.

**3. More in the tray panel.** Expand it to show what is going on:

- Model, voice, wake word and microphone in use.
- **Whether the graphics card is actually being used, and which one.**
  llama.cpp quietly falls back to the processor and there is no way to tell.
  "Why is it slow on my machine" will be the most common question.
- Timings from the last question, already printed to the log.
- What it last looked up. The privacy claim is that only a search query
  leaves the machine; showing the query makes that checkable.
- Memory used against available, and words per second, with a plain verdict -
  *your card has room, a larger model would run fine* - rather than raw
  numbers people have to interpret. Get the memory figures from llama.cpp
  rather than Windows; it reports the same way on every vendor.
- Version, and a button to open the log folder.

The point is bug reports. A tester can screenshot one panel instead of hunting
for a log file.

**4. The installer's download needs a time remaining.** "179 MB of 2777 MB"
says nothing about whether that is five minutes or an hour, and that is when
people decide it has frozen. Everything else about the installer is cosmetic.

## Later

**5. "Hey Gab".** Still using the stock `hey_jarvis` model. The hosted trainer
charges; the free route is the project's own
[Colab notebook](https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb) -
change `config["target_phrase"] = ["hey gab"]`, pick a T4 GPU, run all,
download the `.onnx`, point `config.WAKE_MODEL` at it and update
`config.WAKE_WORD_NAME`.

Bare "Gab" is a bad idea: one syllable, and it will fire on grab, gap, cab and
ordinary speech.

**6. A better voice.** None of the five Piper voices were liked;
`en_GB-cori-high` is a placeholder. Kokoro is the candidate - still local,
still no account, much more natural, around 350 MB.

**7. Personality.** Lives in `config.SYSTEM_PROMPT`. The catch: that prompt
demands "one or two short sentences, no preamble", which is what keeps answers
fast and stops rambling. Personality needs room to breathe, so this is a
balance to tune rather than a line to add. Worth doing with the voice, and
worth checking whether a 4B model can hold a character for a whole answer.

**8. Animations.** The orb repaints 60 times a second already, so this is
design work, not plumbing. Today, appearing and disappearing is a 200ms fade
and nothing else, and the state colour is swapped in one assignment so blue
snaps to purple in a single frame. Blending between palettes is probably the
biggest single win. Keep them quick - slow transitions read as sluggish in
something used a dozen times a day.

**9. Choosing models.** A dropdown in the panel to pick and download a
different model, with suggestions for weak, middling and strong machines.
Needs item 3's usage figures to be useful.

**10. Conversation memory.** Every question stands alone, so no follow-ups.

**11. Repository.** Add a LICENSE - openWakeWord and Piper are Apache-2.0 and
llama.cpp is MIT, all fine, but **read Qwen's model licence** before making the
repo public. Then a description and topics.

## Someday

**Code signing**, to stop the SmartScreen warning. A few hundred dollars a
year, so not a hobby-project decision.

**Conflicting search results.** It takes the most recent, which is not always
right.

## Worth not rediscovering

- **Qwen narrates its reasoning unless `--reasoning off` is passed.** Left on,
  it spends its whole token budget thinking out loud and returns an empty
  answer. Check this if the model is ever swapped.
- **Native tool calling was tried for search and abandoned.** The 4B model
  volunteered a search about half the time, and would announce it needed to
  look something up without doing it. The separate one-line routing question
  gets 21 out of 21.
- **The Vulkan build of llama.cpp is 35 MB**, against 254 MB plus a 391 MB
  runtime for CUDA, and works on AMD, Intel and NVIDIA alike.
- **The installer skips the model download** when the right one is already
  installed, so updating takes under a minute instead of ten.
- **Builds write to `D:\GabBuild`.** The C: drive hit zero bytes free once.

## Done

Wake word, listening, speech to text, answering, web search and weather,
spoken replies, the orb, the tray panel, settings that survive installation,
and a 452 MB installer that fetches its own model.
