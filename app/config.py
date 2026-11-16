import os
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv(
    "NOIR_LLM_BASE_URL",
    "http://localhost:8000/v1"
)

LLM_MODEL = os.getenv(
    "NOIR_LLM_MODEL",
    "mlx-community/Qwen3-0.6B-4bit"
)

LLM_TEMPERATURE = float(os.getenv("NOIR_LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("NOIR_LLM_MAX_TOKENS", "1024"))
LLM_TIMEOUT = float(os.getenv("NOIR_LLM_TIMEOUT", "120"))