
import logging
import os
import tempfile
from pathlib import Path
from pydantic import BaseModel
from fastapi import Response

from app.services.tts_client import synthesize_speech

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.services.transcription import transcribe_audio


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Voice"])

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB

ALLOWED_EXTENSIONS = {
    ".webm", ".wav", ".mp3", ".m4a",
    ".mp4", ".mpeg", ".mpga", ".ogg", ".flac"
}

class SpeechRequest(BaseModel):
    text: str

@router.post("/voice/synthesize")
async def synthesize_voice(request: SpeechRequest):
    audio = await synthesize_speech(request.text)

    return Response(
        content=audio,
        media_type="audio/wav",
    )

@router.post("/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)):
    allowed_content_types = {
        "audio/webm",
        "video/webm",
        "audio/webm;codecs=opus",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp4",
        "video/mp4",
        "audio/ogg",
        "audio/flac",
        "audio/x-flac",
        "audio/aac",
        "audio/mp4a-latm"
    }

    if audio.content_type and audio.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}"
        )

    suffix = Path(audio.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        suffix = ".webm"

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            temp_path = temp_file.name
            total_size = 0

            while chunk := await audio.read(1024 * 1024):
                total_size += len(chunk)

                if total_size > MAX_AUDIO_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Audio file exceeds the 25 MB limit."
                    )

                temp_file.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded audio file is empty."
            )

        result = await run_in_threadpool(
            transcribe_audio,
            temp_path
        )

        return result

    except HTTPException:
        raise

    except Exception:
        logger.exception("Audio transcription failed")

        raise HTTPException(
            status_code=500,
            detail="Audio transcription failed."
        )

    finally:
        await audio.close()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
