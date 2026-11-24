import json
import platform
import subprocess
import urllib.request
from datetime import datetime
import time
from huggingface_hub import hf_hub_download

def get_macos_version():
    result = subprocess.run(
        ["sw_vers", "-productVersion"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()

def get_macos_cpu():
    result = subprocess.run(
        ["sysctl", "-n", "machdep.cpu.brand_string"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()

def get_memory_gb():
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            check=True,
        )
        return round(int(result.stdout.strip()) / (1024 ** 3), 2)

    elif platform.system() == "Windows":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)

        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None

        return round(status.total_physical / (1024 ** 3), 2)

    return None

def get_vllm_version():
    url = "http://localhost:8000/version"

    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.loads(response.read())

    return data["version"]

def get_vllm_model_info():
    url = "http://localhost:8000/v1/models"

    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.loads(response.read())

    models = data.get("data", [])

    if not models:
        raise RuntimeError("No models found in vLLM.")

    return models[0]

def get_vllm_model():
    return get_vllm_model_info()["id"]

def get_macos_gpu():
    result = subprocess.run(
        ["system_profiler", "SPDisplaysDataType"],
        capture_output=True,
        text=True,
        check=True,
    )

    for line in result.stdout.splitlines():
        if "Chipset Model:" in line:
            return line.split(":", 1)[1].strip()

    return None

def get_gpu():
    system = platform.system()

    if system == "Darwin":
        return get_macos_gpu()

    return None

def get_system_info():
    return {
        "os": platform.system(),
        "os_version": get_macos_version() if platform.system() == "Darwin" else platform.release(),
        "architecture": platform.machine(),
        "cpu": get_macos_cpu() if platform.system() == "Darwin" else platform.processor(),
        "memory_gb": get_memory_gb(),
        "python_version": platform.python_version(),
    }

def get_metadata():
    system = get_system_info()

    return {
        "timestamp": datetime.now().astimezone().isoformat(),
        "model": get_model_metadata(),
        "hardware": {
            "cpu": system["cpu"],
            "gpu": get_gpu(),
            "memory_gb": system["memory_gb"],
            "architecture": system["architecture"],
        },
        "software": {
            "os": system["os"],
            "os_version": system["os_version"],
            "python_version": system["python_version"],
            "inference_server": "vLLM",
            "inference_server_version": get_vllm_version(),
            "backend": INFERENCE_BACKEND,
        },
    }

def get_model_config(model_name):
    try:
        config_path = hf_hub_download(
            repo_id=model_name,
            filename="config.json",
        )

        with open(config_path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as error:
        print(f"Warning: Could not retrieve model configuration: {error}")
        return None

def get_model_metadata():
    model_info = get_vllm_model_info()
    model_name = model_info["id"]

    config = get_model_config(model_name)

    quantization = None

    if config:
        quantization = (
            config.get("quantization")
            or config.get("quantization_config")
        )

    return {
        "name": model_name,
        "quantization": quantization,
        "context_length": model_info.get("max_model_len"),
    }

def save_result(result):
    results_path = "benchmark/results.json"

    try:
        with open(results_path, "r", encoding="utf-8") as file:
            results = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        results = []

    results.append(result)

    with open(results_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

def measure_ttft():
    payload = {
        "model": get_vllm_model(),
        "messages": [
            {
                "role": "user",
                "content": BENCHMARK_PROMPT,
            }
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": True,
        "stream_options": {
            "include_usage": True,
        },
    }

    request = urllib.request.Request(
        "http://localhost:8000/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    start_time = time.perf_counter()
    first_token_time = None
    prompt_tokens = None
    generated_tokens = None
    total_tokens = None

    with urllib.request.urlopen(request, timeout=120) as response:
        for line in response:
            line = line.decode("utf-8").strip()

            if not line.startswith("data: "):
                continue

            data = line[6:]

            if data == "[DONE]":
                break

            chunk = json.loads(data)

            usage = chunk.get("usage")

            if usage:
                prompt_tokens = usage["prompt_tokens"]
                generated_tokens = usage["completion_tokens"]
                total_tokens = usage["total_tokens"]
                continue

            content = chunk["choices"][0]["delta"].get("content", "")

            if content and first_token_time is None:
                first_token_time = time.perf_counter()
        
        end_time = time.perf_counter()
        total_latency_ms = (end_time - start_time) * 1000
        # print(f"Total latency: {total_latency_ms:.2f} ms")


    if first_token_time is not None:
        ttft_ms = (first_token_time - start_time) * 1000
        # print(f"TTFT: {ttft_ms:.2f} ms")
    else:
        raise RuntimeError("TTFT measurement failed: No generated content received.")

    generation_time_ms = total_latency_ms - ttft_ms

    if generated_tokens is not None and generation_time_ms > 0:
        tokens_per_second = generated_tokens / (generation_time_ms / 1000)
        print(f"Generation speed: {tokens_per_second:.2f} tokens/s")

    result = get_metadata()

    result["benchmark"] = {
        "prompt_tokens": prompt_tokens,
        "output_tokens": generated_tokens,
        "ttft_ms": round(ttft_ms, 2),
        "generation_tokens_per_second": round(tokens_per_second, 2),
        "total_latency_ms": round(total_latency_ms, 2),
    }

    save_result(result)
    print("Benchmark result saved.")

    

BENCHMARK_PROMPT = "Explain what a computer is in one short sentence."
MAX_TOKENS = 64
TEMPERATURE = 0.0
INFERENCE_BACKEND = "MLX/Metal"

metadata = get_metadata()
print(json.dumps(metadata, indent=2))

measure_ttft()