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

**Status:** design only; barge-in has not yet been implemented or validated.
