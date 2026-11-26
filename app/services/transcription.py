
from pathlib import Path

import mlx_whisper


MODEL_ID = "mlx-community/whisper-tiny"


def transcribe_audio(audio_path: str | Path) -> dict[str, str]:
    """
    Transcribe an audio file using local MLX Whisper.

    Returns:
        {
            "text": Transcribed text,
            "language": Detected language
        }
    """

    audio_path = Path(audio_path)

    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=MODEL_ID
    )

    return {
        "text": result["text"].strip(),
        "language": result["language"]
    }
