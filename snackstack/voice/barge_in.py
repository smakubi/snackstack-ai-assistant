"""Experimental half-duplex agent with interruptible playback.

Use headphones: energy VAD cannot distinguish speaker echo from real speech.
"""
import threading

from snackstack.logger import setup_logger

logger = setup_logger("snackstack.barge_in")


class BargeInController:
    def __init__(self, recorder, speaker):
        self.recorder = recorder
        self.speaker = speaker

    def speak_and_listen(self, text):
        """Speak while capturing microphone. Return transcribed interruption, if any."""
        cancel_playback = threading.Event()
        stop_listening = threading.Event()
        captured = []
        failures = []

        def listener():
            try:
                audio = self.recorder.record_vad(
                    max_duration=30,
                    start_timeout=30,
                    silence_duration=0.8,
                    on_speech_start=cancel_playback.set,
                    stop_event=stop_listening,
                )
                if len(audio) and cancel_playback.is_set():
                    captured.append(audio)
            except Exception as exc:
                failures.append(exc)
                logger.exception("Barge-in microphone failed")

        worker = threading.Thread(target=listener, daemon=True)
        worker.start()
        try:
            self.speaker.speak_streaming(text, cancel_event=cancel_playback)
        finally:
            if not cancel_playback.is_set():
                stop_listening.set()
            worker.join(timeout=32)
        if worker.is_alive():
            logger.warning("Barge-in microphone did not stop promptly")
        if failures:
            logger.warning("Barge-in disabled for this turn due to microphone error")
        if captured:
            transcript = self.recorder.transcribe(captured[0]).strip()
            logger.info("Interruption transcribed: %s", transcript)
            return transcript
        return ""
