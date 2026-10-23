"""
voice/recorder.py — Microphone recording + OpenAI Whisper transcription.
"""

import io
import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_HW_AVAILABLE = True
except ImportError:
    AUDIO_HW_AVAILABLE = False

from snackstack.config import openai_client
from snackstack.logger import setup_logger

logger = setup_logger("snackstack.recorder")


class VoiceRecorder:
    """Record from the microphone and transcribe with Whisper."""

    def __init__(self, sample_rate: int = 16_000):
        self.sample_rate = sample_rate

    # ── recording ───────────────────────────────────────────
    def record_audio(self, duration: int = 5) -> np.ndarray:
        """Capture audio from the default input device."""
        if not AUDIO_HW_AVAILABLE:
            raise RuntimeError("Microphone support unavailable. Run uv sync and check sounddevice installation.")

        logger.info("Recording for %ds — speak now!", duration)
        try:
            audio = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
            )
            sd.wait()
        except Exception as exc:
            raise RuntimeError("Could not record microphone audio. Check macOS microphone permission and input device.") from exc
        logger.info("Recording complete")
        return audio.flatten()

    # ── transcription ───────────────────────────────────────
    def transcribe(self, audio: np.ndarray) -> str:
        """Send a numpy audio array to Whisper and return the text."""
        if not AUDIO_HW_AVAILABLE:
            raise RuntimeError("Audio dependencies are not installed.")
        if not np.any(np.abs(audio) > 0.001):
            logger.warning("No microphone signal detected. Check input device and microphone permissions.")
            return ""
        buf = io.BytesIO()
        if AUDIO_HW_AVAILABLE:
            sf.write(buf, audio, self.sample_rate, format="WAV")
        buf.seek(0)
        buf.name = "audio.wav"

        try:
            resp = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=buf,
            )
            return resp.text.strip()
        except Exception as exc:
            logger.error("Whisper error: %s", exc)
            return ""

    # ── convenience ─────────────────────────────────────────
    def record_and_transcribe(self, duration: int = 5) -> tuple[np.ndarray, str]:
        """Record then transcribe in one call."""
        audio = self.record_audio(duration)
        text = self.transcribe(audio)
        logger.info("Transcription: %s", text)
        return audio, text
