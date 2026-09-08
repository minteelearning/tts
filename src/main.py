import hmac
import os
from collections.abc import AsyncIterator

import edge_tts
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title="Mintee Mandarin TTS", version="0.1.0", docs_url=None, redoc_url=None)

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
SUPPORTED_VOICES = {
    "zh-CN-XiaoxiaoNeural",  # Mandarin, feminine
    "zh-CN-XiaoyiNeural",  # Mandarin, feminine
    "zh-CN-YunxiNeural",  # Mandarin, masculine
    "zh-CN-YunjianNeural",  # Mandarin, masculine
}


class SpeechRequest(BaseModel):
    input: str = Field(min_length=1, max_length=1_200)
    voice: str = DEFAULT_VOICE
    rate: str = Field(default="+0%", pattern=r"^[+-](?:[0-9]|[1-9][0-9]|100)%$")


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    configured_key = os.environ.get("TTS_API_KEY")
    supplied_key = authorization.removeprefix("Bearer ") if authorization else ""

    if not configured_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS is unavailable")
    if not hmac.compare_digest(supplied_key, configured_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


async def audio_chunks(text: str, voice: str, rate: str) -> AsyncIterator[bytes]:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "mintee-mandarin-tts"}


@app.post("/v1/audio/speech", dependencies=[Depends(require_api_key)])
async def create_speech(request: SpeechRequest) -> Response:
    if request.voice not in SUPPORTED_VOICES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported voice")

    try:
        audio = bytearray()
        async for chunk in audio_chunks(request.input.strip(), request.voice, request.rate):
            audio.extend(chunk)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speech provider did not return audio",
        ) from error

    if not audio:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Speech provider returned no audio")

    return Response(
        content=bytes(audio),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
