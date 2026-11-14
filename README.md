# Noir

A private, local AI assistant designed to serve as a personal intelligence and productivity system.

## Tech Stack

- Python
- FastAPI
- SQLite
- HTML, CSS and JavaScript

## Current Features

- Local web-based chat interface
- Conversation management
- Persistent conversation history
- Local SQLite storage

## Setup

Clone the repository and navigate to its directory.

Create and activate a virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate

Install dependencies:

    python -m pip install -r requirements.txt

Run the application:

    uvicorn app.main:app --reload

Open http://127.0.0.1:8000 in your browser.

## Development Status

Noir is under active development. Local LLM integration, streaming, voice interaction, memory and RAG are planned features.