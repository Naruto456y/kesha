"""
Распознавание речи через Aqua Voice (Avalon API, совместим с OpenAI).
Доки: https://aquavoice.com/avalon-api/docs  ·  ключ: https://app.aquavoice.com/api-dashboard

stt(wav_path, language="ru") -> str       (бросает исключение при ошибке)
AquaRecognizer(local)                      (того же вида, что GigaAMRecognizer; при сбое Aqua -> local)
"""
import io
import os
import time
import wave
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BASE_URL = "https://api.aquavoice.com/v1"
MODEL = "avalon-v1.5"
TIMEOUT = 4.0          # с; не ответил — сразу GigaAM офлайн, ждать дольше голосовому ассистенту незачем
COOLDOWN = 60.0        # после сбоя Aqua не трогаем столько секунд (не копим задержки офлайн)

_client = None


def available():
    return bool(os.environ.get("AQUA_API_KEY", "").strip())


def _get_client():
    global _client
    if _client is None:
        import httpx
        from openai import OpenAI
        verify = True
        try:  # антивирус с перехватом TLS: certifi его корень не знает, Windows — знает
            import ssl
            import truststore
            verify = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except Exception:
            pass
        _client = OpenAI(base_url=BASE_URL, api_key=os.environ["AQUA_API_KEY"].strip(),
                         timeout=TIMEOUT, max_retries=0,
                         http_client=httpx.Client(verify=verify, timeout=TIMEOUT))
    return _client


def _transcribe(fileobj, language):
    kw = {"model": MODEL, "file": fileobj}
    if language:
        kw["language"] = language
    return (_get_client().audio.transcriptions.create(**kw).text or "").strip()


def stt(wav_path, language="ru"):
    """Файл (wav/mp3/…) -> текст. Исключение, если ключа нет или Aqua не ответила."""
    if not available():
        raise RuntimeError("AQUA_API_KEY не задан")
    with open(wav_path, "rb") as f:
        return _transcribe(f, language)


def stt_pcm(audio_bytes, sample_rate=16000, language="ru"):
    """Сырой PCM int16 mono -> текст (упаковывает в WAV в памяти)."""
    if not available():
        raise RuntimeError("AQUA_API_KEY не задан")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(audio_bytes)
    buf.seek(0)
    buf.name = "speech.wav"
    return _transcribe(buf, language)


class AquaRecognizer:
    """Интерфейс GigaAMRecognizer.recognize(); Aqua -> при любой ошибке локальный `local`."""

    def __init__(self, local, language="ru"):
        self.local = local
        self.language = language
        self._down_until = 0.0
        self.last_ms = 0
        self.last_engine = ""

    def recognize(self, audio_bytes, sample_rate=16000, normalize_text=True, local_only=False):
        from voice.gigaam_recognizer import normalize
        if not audio_bytes or len(audio_bytes) < int(sample_rate * 2 * 0.2):
            return ""
        t0 = time.time()
        if not local_only and available() and time.time() >= self._down_until:
            try:
                text = stt_pcm(audio_bytes, sample_rate, self.language)
                self.last_ms = int((time.time() - t0) * 1000)
                self.last_engine = "aqua"
                return normalize(text) if normalize_text else text
            except Exception as e:
                self._down_until = time.time() + COOLDOWN
                print(f"[aqua] недоступна ({type(e).__name__}: {str(e)[:120]}), "
                      f"перехожу на локальный STT на {int(COOLDOWN)} с")
        text = self.local.recognize(audio_bytes, sample_rate, normalize_text)
        self.last_ms = int((time.time() - t0) * 1000)
        self.last_engine = "local"
        return text

    def recognize_file(self, path, normalize_text=True):
        from voice.gigaam_recognizer import normalize
        if available() and time.time() >= self._down_until:
            try:
                text = stt(path, self.language)
                return normalize(text) if normalize_text else text
            except Exception as e:
                self._down_until = time.time() + COOLDOWN
                print(f"[aqua] недоступна ({type(e).__name__}), локальный STT")
        return self.local.recognize_file(path, normalize_text)
