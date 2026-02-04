# AutoRAG

AutoRAG is a Retrieval-Augmented Generation (RAG) system that creates a Telegram bot capable of mimicking a specific persona. By indexing a message history file, the bot adopts the slang, tone, and writing style of the original author.

## Features

- **Persona Mimicry**: Uses RAG to ground LLM responses in a provided message history.
- **Dynamic Model Switching**: Supports multiple Ollama models (e.g., Qwen, Gemma).
- **User Management API**: Built-in endpoints to dynamically add or remove authorized Telegram users.
- **Security**: Access is restricted to a configurable list of Telegram User IDs stored in Redis.
- **Production Ready**: Includes Docker Compose configurations for both GPU (NVIDIA) and CPU-only environments.
- **GitLab CI/CD**: Pre-configured pipeline for building and pushing Docker images.

## Architecture

- **Backend**: FastAPI providing the chat logic and user management.
- **Vector Database**: Redis (Redis Stack) for high-performance vector similarity search.
- **LLM Engine**: Ollama (running locally or in a container).
- **Telegram Bot**: Python-based bot using `python-telegram-bot`.

## Installation & Setup

### Prerequisites
- Docker and Docker Compose
- (Optional) NVIDIA Container Toolkit for GPU acceleration
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### 1. Prepare Data
Place your persona's message history in a file named `messages.txt` in the root directory.

### 2. Run with Docker Compose

**For NVIDIA GPU Acceleration:**
```bash
export TELEGRAM_TOKEN="your_telegram_bot_token"
docker-compose up -d --build
```

**For CPU Only:**
```bash
export TELEGRAM_TOKEN="your_telegram_bot_token"
docker-compose -f docker-compose-noGPU.yml up -d --build
```

### 3. Initialize Models
Once the containers are running, you must pull the required models into the Ollama container:
```bash
docker-compose exec ollama ollama pull bge-m3
docker-compose exec ollama ollama pull qwen3:4b
```

## User Management API

You can manage authorized users via the FastAPI backend (default port `8000`):

- **List Users**: `GET /users`
- **Add User**: `POST /users` (Body: `{"user_id": 12345678}`)
- **Remove User**: `DELETE /users/{user_id}`

## Configuration

Environment variables can be adjusted in the `docker-compose` files:
- `TELEGRAM_TOKEN`: Your bot token.
- `EMBEDDING_MODEL`: Defaults to `bge-m3`.
- `OLLAMA_BASE_URL`: Connection string for the Ollama service.
- `REDIS_URL`: Connection string for the Redis service.

## Author
Giuseppe Marco Randazzo <gmrandazzo@gmail.com>

