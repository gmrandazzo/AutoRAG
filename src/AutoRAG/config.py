
import os

# Configuration
TEXT_FILE_PATH = os.getenv("TEXT_FILE_PATH", "messages.txt")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
INDEX_NAME = "persona-embeddings"
ALLOWED_USERS_SET = "allowed_users"
PROMPT_TEMPLATE_KEY = "persona_prompt_template"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000/chat")

DEFAULT_ALLOWED_USERS = []
