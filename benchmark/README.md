# LLM Inference Benchmark

## Purpose

This benchmark measures the inference performance of the LLM deployed through vLLM-Metal on Apple Silicon.

It establishes a reproducible baseline for evaluating model inference performance as Noir evolves.

The benchmark currently measures:
- **Time to First Token (TTFT):** Time taken to receive the first generated content.
- **Generation Speed:** Number of output tokens generated per second.
- **Total Latency:** Time taken to complete the entire generation request.

## Architecture

The benchmark communicates directly with the vLLM OpenAI-compatible API.

```text
Benchmark Script
       |
       v
vLLM OpenAI-compatible API
       |
       v
   vLLM-Metal
       |
       v
    MLX / Metal
       |
       v
   Qwen3 Model
```

This isolates inference benchmarking from Noir's application layer. FastAPI, the frontend, and database operations are not included in these measurements.

## Setup

### 1. Start the inference server

Activate the vLLM environment:

```bash
source ~/.venv-vllm-metal/bin/activate
```

Start the model server:

```bash
vllm serve mlx-community/Qwen3-1.7B-4bit --max-model-len 2048
```

The server exposes an OpenAI-compatible API on port `8000`.

### 2. Run the benchmark

From the Noir project root, run:

```bash
python benchmark/benchmark.py
```

The benchmark performs:
1. One warm-up run, excluded from saved measurements.
2. Five measured inference runs.
3. Statistical analysis of the five measured runs.

Results are appended to `benchmark/results.json`.

## Metrics

The benchmark collects the following measurements for each inference request.

### Time to First Token (TTFT)

Measures the time between sending the request and receiving the first non-empty generated content.

```text
TTFT = First generated content timestamp - Request start timestamp
```

### Generation Speed

Measures the average output generation throughput after the first generated content is received. This is end-to-end streamed generation throughput, not raw GPU or model-decoding throughput.

```text
Generation Speed = Output Tokens / Generation Time
```

Where:

```text
Generation Time = Total Latency - TTFT
```

The result is expressed in tokens per second.

### Total Latency

Measures the time between sending the request and completing the streamed response.

```text
Total Latency = Stream Completion Timestamp - Request Start Timestamp
```

### Token Usage

Token counts are obtained from the final usage information returned by vLLM, rather than estimating tokens from the number of streaming chunks.

The benchmark records:
- Prompt tokens
- Completion tokens

## Benchmark Environment

The benchmark automatically collects hardware, software, and model metadata alongside each measurement.

### Hardware

| Component | Configuration |
|---|---|
| CPU | Apple M3 Max |
| GPU | Apple M3 Max |
| Unified Memory | 128 GB |
| Architecture | arm64 |

### Software

| Component | Version / Configuration |
|---|---|
| Operating System | macOS 26.7.3 |
| Python | 3.14.3 |
| Inference Server | vLLM 0.33.0 |
| Backend | MLX / Metal |

### Model

| Property | Configuration |
|---|---|
| Model | `mlx-community/Qwen3-1.7B-4bit` |
| Quantization | 4-bit |
| Group Size | 64 |
| Active Context Length | 2048 tokens |

This metadata is collected automatically by the benchmark script and stored with each result.

## Initial Performance Baseline

**Date:** November 24, 2026

**Model:** `mlx-community/Qwen3-1.7B-4bit`

**Workload:**
- Prompt: `Explain what a computer is in one short sentence.`
- Prompt tokens: 19
- Maximum completion tokens: 64
- Temperature: 0.0
- Warm-up runs: 1
- Measured runs: 5

### Results

| Metric | Mean | Median | Min | Max | Std. Dev. |
|---|---:|---:|---:|---:|---:|
| TTFT (ms) | 23.12 | 23.59 | 21.46 | 23.72 | 0.95 |
| Generation Speed (tokens/s) | 219.36 | 219.01 | 218.43 | 220.53 | 1.00 |
| Total Latency (ms) | 314.89 | 314.07 | 313.44 | 316.64 | 1.60 |

All five measured runs generated 64 completion tokens.

These measurements represent warm-model inference performance. Model loading and cold-start latency are not included.

## Limitations and Interpretation

The current benchmark provides an initial inference performance baseline, but it has several limitations.

### Workload

- Uses a single fixed prompt containing 19 input tokens.
- Limits generated output to 64 tokens.
- Uses a temperature of 0.0 for deterministic generation.
- Performs one warm-up run followed by five measured runs.

These settings provide a consistent workload but do not represent every possible inference scenario.

### Measurement Scope

- Measures inference directly through the vLLM API.
- Excludes FastAPI, frontend, database, and other application-level overhead.
- Includes HTTP communication, streaming, and inference-server overhead.
- Measures warm-model performance rather than model loading or cold-start time.

### Statistical Limitations

- Uses only five measured runs per benchmark session.
- Reports sample standard deviation.
- Does not currently measure performance under concurrent requests or sustained workloads.

### Future Improvements

Potential extensions include:

- Testing different prompt and output lengths.
- Comparing different model sizes and quantization levels.
- Measuring concurrent inference performance.
- Evaluating application-level latency through Noir's FastAPI backend.
- Measuring memory consumption and sustained performance.

The current results should therefore be treated as a reproducible starting point for future comparisons, not a comprehensive evaluation of inference performance.