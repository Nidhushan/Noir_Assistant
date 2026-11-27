import httpx

TTS_URL = "http://127.0.0.1:8002/synthesize"


async def synthesize_speech(text: str) -> bytes:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            TTS_URL,
            json={"text": text},
        )

        response.raise_for_status()

        return response.content