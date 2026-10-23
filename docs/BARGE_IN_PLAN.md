# Voice barge-in experiment (isolated branch)

This branch is for prototyping user interruptions during assistant speech. The stable `main` branch remains half-duplex.

## Intended behavior

1. Keep microphone capture active while TTS is playing.
2. Detect a real user utterance rather than speaker echo or ambient noise.
3. Stop current TTS playback promptly and cancel any in-flight speech stream.
4. Buffer pre-roll and capture the complete new utterance with VAD.
5. Transcribe it, send it through LangGraph with the existing conversation thread, then speak the new response.
6. Recover safely from cancellation, audio device errors, and false triggers.

## Proposed implementation

- Separate audio capture, speech playback, and conversation orchestration into cancellable tasks.
- Use a dedicated microphone capture loop and a playback stop/cancellation signal.
- Start with headphones to minimize echo; energy-based VAD alone is not reliable for barge-in through speakers.
- Add a speech detector with hysteresis (consecutive positive frames), pre-roll, and a cooldown to avoid false triggers.
- For speaker playback, consider acoustic echo cancellation or explicit playback-reference suppression before claiming reliable hands-free barge-in.
- Ensure interrupted TTS does not leave orphaned output streams or stale responses.
- Keep `--continuous` unchanged on main. Gate experimental behavior behind a separate `--barge-in` flag on this branch.

## Acceptance checks

- User interrupts a long TTS answer and playback stops quickly.
- New user utterance is transcribed without losing its first syllable.
- Speaker audio alone does not trigger interruption.
- Short pauses and ambient noise do not cause accidental cancellation.
- Multiple rapid interruptions do not crash or corrupt LangGraph state.
- Ctrl+C cleanly releases microphone and speaker resources.
- Existing `--voice --vad --stream --continuous` remains functional.

**Status:** experimental implementation committed on this branch; not yet tested on real hardware. This is interruptible half-duplex response handling, not full-duplex simultaneous generation.

## Try it (headphones strongly recommended)

```bash
git fetch origin
git switch feature/voice-barge-in
git pull origin feature/voice-barge-in
uv sync
uv run snackstack --voice --vad --stream --continuous --barge-in
```

Ask: "Tell me about every dish on the menu." While the assistant speaks, say "Actually, what is vegan?" The experimental microphone listener should detect your speech, cancel PCM playback, finish capturing the utterance, transcribe it, and run the new query. Use Ctrl+C to stop. Compare with the stable command without `--barge-in`.

**Limitations:** Use headphones; there is no acoustic echo cancellation, so speakers can self-trigger. This is energy threshold detection, not neural VAD or speaker verification. It cannot interrupt while the LLM is thinking or Whisper is transcribing. Interruptions during human-in-the-loop prompts are not fully handled. Microphone/audio behavior must be tested on your machine before classroom or production use.
