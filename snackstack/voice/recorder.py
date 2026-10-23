"""
voice/recorder.py — Microphone recording + OpenAI Whisper transcription.
"""

import io
import collections
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

    def record_vad(self, max_duration: float = 20, silence_duration: float = 1.0,
                   threshold: float = 0.012, start_timeout: float = 8.0) -> np.ndarray:
        """Record until speech ends using a lightweight RMS energy detector.

        This is energy-based VAD, not a neural speech classifier. Works offline.
        """
        if not AUDIO_HW_AVAILABLE:
            raise RuntimeError("Microphone support unavailable. Run uv sync.")
        blocksize = int(self.sample_rate * 0.03)
        pre_roll = collections.deque(maxlen=12)
        frames = []
        started = False
        quiet = 0.0
        elapsed = 0.0
        logger.info("Listening — speak now (up to %.0fs)", max_duration)
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1,
                                dtype="float32", blocksize=blocksize) as stream:
                while elapsed < max_duration:
                    block, overflow = stream.read(blocksize)
                    if overflow:
                        logger.warning("Microphone input overflow")
                    chunk = block[:, 0].copy()
                    elapsed += len(chunk) / self.sample_rate
                    rms = float(np.sqrt(np.mean(chunk * chunk)))
                    active = rms >= threshold
                    if not started:
                        pre_roll.append(chunk)
                        if active:
                            started = True
                            frames.extend(pre_roll)
                            logger.info("Speech detected")
                        elif elapsed >= start_timeout:
                            logger.warning("No speech detected within %.1fs", start_timeout)
                            break
                    else:
                        frames.append(chunk)
                        quiet = 0.0 if active else quiet + len(chunk) / self.sample_rate
                        if quiet >= silence_duration:
                            logger.info("End of speech detected")
                            break
        except Exception as exc:
            raise RuntimeError("Microphone recording failed. Check macOS permissions and input device.") from exc
        return np.concatenate(frames) if started and frames else np.empty(0, dtype=np.float32)

    def record_and_transcribe_vad(self, max_duration: float = 20) -> tuple[np.ndarray, str]:
        audio = self.record_vad(max_duration=max_duration)
        text = self.transcribe(audio) if len(audio) else ""
        logger.info("Transcription: %s", text)
        return audio, text

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
