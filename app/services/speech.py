from pathlib import Path
from kokoro_mlx import KokoroTTS

MODEL = KokoroTTS.from_pretrained()
VOICE = "am_michael"


def synthesize_speech(text: str, output_path: str | Path) -> None:
    MODEL.save(text, str(output_path), voice=VOICE)