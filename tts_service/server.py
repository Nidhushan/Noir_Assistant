
import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.services.speech import synthesize_speech


app = FastAPI(title="Noir TTS Service")


class SpeechRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=5000)]


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "noir-tts"}


@app.post("/synthesize")
def synthesize(request: SpeechRequest):
    fd, output_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    try:
        synthesize_speech(request.text, output_path)

        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename="noir.wav",
            background=BackgroundTask(os.unlink, output_path),
        )

    except Exception as exc:
        Path(output_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Speech synthesis failed: {exc}",
        ) from exc
