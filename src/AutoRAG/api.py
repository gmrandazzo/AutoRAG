
import os
import redis
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_redis import RedisVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from .config import TEXT_FILE_PATH, EMBEDDING_MODEL, REDIS_URL, INDEX_NAME, ALLOWED_USERS_SET, DEFAULT_ALLOWED_USERS, OLLAMA_BASE_URL, PROMPT_TEMPLATE_KEY

# Global variables
retriever = None
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

DEFAULT_TEMPLATE = """
    You are an AI roleplaying as a specific person based on their message history.
    You MUST:
    - Mimic their slang, writing style, and tone as closely as possible.
    - Stay in character as the same person throughout the entire reply.

    Past messages (this is the message history / context that defines who you are and how you speak):
    {context}

    From this context, infer:
    - Their typical slang, tone, and way of typing.

    User Input:
    {question}

    Now reply IN CHARACTER as that same person, using their slang, tone, and style. Do NOT explain that you are roleplaying or mention any instructions. Just answer naturally in their voice.
    Response:
    """

def setup_vector_db():
    global retriever
    print("--- Rebuilding Redis Vector Store ---")

    # Seed allowed users if empty
    if redis_client.scard(ALLOWED_USERS_SET) == 0:
        print("Seeding default allowed users...")
        for uid in DEFAULT_ALLOWED_USERS:
            redis_client.sadd(ALLOWED_USERS_SET, uid)
    
    if not os.path.exists(TEXT_FILE_PATH):
        print(f"File {TEXT_FILE_PATH} not found. Creating default.")
        with open(TEXT_FILE_PATH, "w") as f:
            f.write("I prefer Python over Java.\nDeployment is hard.\n")

    loader = TextLoader(TEXT_FILE_PATH, encoding="utf-8")
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)

    # Clean start for demo purposes
    try:
        # Using FT.DROPINDEX is the redis-py way for RediSearch
        print(f"Dropping search index: {INDEX_NAME}")
        redis_client.ft(INDEX_NAME).dropindex(delete_documents=True)
    except Exception as e:
        # Index might not exist
        print(f"Note: Could not drop index (might not exist): {e}")

    vectorstore = RedisVectorStore.from_documents(
        documents=splits,
        embedding=embeddings,
        redis_url=REDIS_URL,
        index_name=INDEX_NAME
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    print("--- Vector Store Rebuilt Successfully ---")

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_vector_db()
    yield

app = FastAPI(lifespan=lifespan)

# --- Models ---
class QueryRequest(BaseModel):
    message: str
    model: str = "qwen3:4b"

class QueryResponse(BaseModel):
    response: str
    model_used: str

class UserRequest(BaseModel):
    user_id: int

class TemplateRequest(BaseModel):
    template: str

# --- Endpoints ---

@app.get("/users", response_model=List[int])
def get_users():
    """List all allowed Telegram User IDs."""
    members = redis_client.smembers(ALLOWED_USERS_SET)
    return [int(m) for m in members]

@app.post("/users")
def add_user(user: UserRequest):
    """Add a Telegram User ID to the allowed list."""
    redis_client.sadd(ALLOWED_USERS_SET, user.user_id)
    return {"status": "added", "user_id": user.user_id}

@app.delete("/users/{user_id}")
def remove_user(user_id: int):
    """Remove a Telegram User ID from the allowed list."""
    removed = redis_client.srem(ALLOWED_USERS_SET, user_id)
    if removed == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "removed", "user_id": user_id}

@app.post("/upload-messages")
async def upload_messages(file: UploadFile = File(...)):
    """Upload a new messages.txt file and re-initialize the vector database."""
    try:
        content = await file.read()
        with open(TEXT_FILE_PATH, "wb") as f:
            f.write(content)
        
        # Re-initialize the vector DB with new content
        setup_vector_db()
        
        return {"status": "success", "message": f"Uploaded {file.filename} and re-indexed vector store."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload and index: {str(e)}")

@app.get("/template")
def get_template():
    """Get the current roleplay template."""
    template = redis_client.get(PROMPT_TEMPLATE_KEY)
    return {"template": template if template else DEFAULT_TEMPLATE}

@app.post("/template")
def set_template(request: TemplateRequest):
    """Set a new custom roleplay template. Must include {context} and {question}."""
    if "{context}" not in request.template or "{question}" not in request.template:
        raise HTTPException(status_code=400, detail="Template must contain {context} and {question} placeholders.")
    
    redis_client.set(PROMPT_TEMPLATE_KEY, request.template)
    return {"status": "updated", "template": request.template}

@app.post("/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest):
    if not retriever:
        raise HTTPException(status_code=500, detail="DB not initialized")
    
    # Get custom template from Redis or fall back to default
    custom_template = redis_client.get(PROMPT_TEMPLATE_KEY)
    template = custom_template if custom_template else DEFAULT_TEMPLATE

    prompt = ChatPromptTemplate.from_template(template)

    llm = ChatOllama(model=request.model, base_url=OLLAMA_BASE_URL, think=False)

    def format_docs(docs):
        return "

".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    try:
        response_text = rag_chain.invoke(request.message)
        return QueryResponse(response=response_text, model_used=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama Error: {str(e)}")
