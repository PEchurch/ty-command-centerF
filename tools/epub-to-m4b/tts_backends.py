"""Pluggable text-to-speech backends for chapter narration.

Every backend exposes the same `synthesize(text, out_path, voice)` method,
so epub_to_m4b.py doesn't need to care which one is in use. Add a new
provider by subclassing TTSBackend and registering it in _BACKENDS below.
"""
from __future__ import annotations

import abc
import os
from pathlib import Path


class TTSBackend(abc.ABC):
    name = 'base'
    default_voice = ''

    @abc.abstractmethod
    def synthesize(self, text: str, out_path: Path, voice: str) -> None:
        """Write synthesized speech for `text` to `out_path`. Any container
        ffmpeg can read (wav/mp3/etc.) is fine — the pipeline normalizes it."""


class OpenAIBackend(TTSBackend):
    """OpenAI text-to-speech. Requires OPENAI_API_KEY. Good default quality/price."""

    name = 'openai'
    default_voice = 'alloy'

    def __init__(self, model: str = 'gpt-4o-mini-tts'):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package is required for --backend openai. "
                "Install with: pip install openai"
            ) from exc
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise RuntimeError(
                'OPENAI_API_KEY is not set. Export it, or put it in a .env file '
                '(see .env.example) and load it before running.'
            )
        self._client = OpenAI(api_key=api_key)
        self.model = model

    def synthesize(self, text: str, out_path: Path, voice: str) -> None:
        with self._client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=voice or self.default_voice,
            input=text,
            response_format='wav',
        ) as response:
            response.stream_to_file(out_path)


class ElevenLabsBackend(TTSBackend):
    """ElevenLabs text-to-speech. Requires ELEVENLABS_API_KEY. Premium quality/price."""

    name = 'elevenlabs'
    default_voice = 'rachel'
    _VOICE_IDS = {
        'rachel': '21m00Tcm4TlvDq8ikWAM',
        'adam': 'pNInz6obpgDQGcFmaJgB',
        'bella': 'EXAVITQu4vr4xnSDxMaL',
        'antoni': 'ErXwobaYiN019PkySvjV',
        'brian': 'nPczCjzI2devNBz1zQrb',
    }

    def __init__(self, model: str = 'eleven_multilingual_v2'):
        api_key = os.environ.get('ELEVENLABS_API_KEY')
        if not api_key:
            raise RuntimeError(
                'ELEVENLABS_API_KEY is not set. Export it, or put it in a .env file '
                '(see .env.example) and load it before running.'
            )
        self._api_key = api_key
        self.model = model

    def synthesize(self, text: str, out_path: Path, voice: str) -> None:
        import requests

        voice_key = (voice or self.default_voice).lower()
        voice_id = self._VOICE_IDS.get(voice_key, voice or self._VOICE_IDS[self.default_voice])
        resp = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
            headers={'xi-api-key': self._api_key, 'Content-Type': 'application/json'},
            json={'text': text, 'model_id': self.model},
            timeout=120,
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)


class InworldBackend(TTSBackend):
    """Inworld AI text-to-speech. Requires INWORLD_API_KEY. Pay-as-you-go pricing
    with no subscription tier, and noticeably cheaper than ElevenLabs per character
    while ranking near the top of independent TTS-quality leaderboards."""

    name = 'inworld'
    default_voice = 'Sarah'

    def __init__(self, model: str = 'inworld-tts-1.5-max'):
        api_key = os.environ.get('INWORLD_API_KEY')
        if not api_key:
            raise RuntimeError(
                'INWORLD_API_KEY is not set. Export it, or put it in a .env file '
                '(see .env.example) and load it before running.'
            )
        self._api_key = api_key
        self.model = model

    def synthesize(self, text: str, out_path: Path, voice: str) -> None:
        import base64
        import requests

        resp = requests.post(
            'https://api.inworld.ai/tts/v1/voice',
            headers={'Authorization': f'Basic {self._api_key}', 'Content-Type': 'application/json'},
            json={
                'text': text,
                'voiceId': voice or self.default_voice,
                'modelId': self.model,
                'audioConfig': {'audioEncoding': 'MP3', 'sampleRateHertz': 24000},
            },
            timeout=120,
        )
        resp.raise_for_status()
        out_path.write_bytes(base64.b64decode(resp.json()['audioContent']))


class LocalBackend(TTSBackend):
    """Free, fully offline fallback via pyttsx3 (needs a system TTS engine,
    e.g. espeak-ng on Linux). Robotic quality — fine for drafts/QC, not
    recommended for a paid audiobook."""

    name = 'local'
    default_voice = ''

    def __init__(self):
        try:
            import pyttsx3  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "The 'pyttsx3' package (plus a system TTS engine, e.g. espeak-ng) "
                "is required for --backend local. Install with: pip install pyttsx3"
            ) from exc

    def synthesize(self, text: str, out_path: Path, voice: str) -> None:
        import pyttsx3

        engine = pyttsx3.init()
        if voice:
            for v in engine.getProperty('voices'):
                if voice.lower() in (v.id or '').lower() or voice.lower() in (v.name or '').lower():
                    engine.setProperty('voice', v.id)
                    break
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()


_BACKENDS = {
    'openai': OpenAIBackend,
    'elevenlabs': ElevenLabsBackend,
    'inworld': InworldBackend,
    'local': LocalBackend,
}


def get_backend(name: str, **kwargs) -> TTSBackend:
    try:
        cls = _BACKENDS[name]
    except KeyError as exc:
        raise ValueError(f'Unknown TTS backend {name!r}. Choose from: {", ".join(_BACKENDS)}') from exc
    return cls(**kwargs)
