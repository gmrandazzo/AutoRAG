#!/bin/bash
# Start the API in the background
echo "Starting AutoRAG API..."
uvicorn AutoRAG.api:app --host 0.0.0.0 --port 8000 &

# Wait for API to be ready (optional but good practice)
sleep 5

# Start the Bot
echo "Starting Telegram Bot..."
autorag-bot
