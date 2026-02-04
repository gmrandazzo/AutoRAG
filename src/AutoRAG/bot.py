
import logging
import httpx
import re
import redis
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from .config import TELEGRAM_TOKEN, API_URL, REDIS_URL, ALLOWED_USERS_SET

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Redis Client for Auth
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def clean_response(text: str) -> str:
    """
    Removes <think> tags and internal reasoning from the LLM output.
    """
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = cleaned.replace("<|im_start|>", "").replace("<|im_end|>", "")
    return cleaned.strip()

def is_authorized(update: Update) -> bool:
    """
    Checks if the user's ID matches the allowlist in Redis.
    """
    user = update.effective_user
    if not user:
        return False
        
    # Check if the user ID is in the Redis set
    if redis_client.sismember(ALLOWED_USERS_SET, user.id):
        return True
    
    # --- PRINT UNAUTHORIZED ID ---
    print(f"⚠️ UNAUTHORIZED ACCESS ATTEMPT! User ID: {user.id} | Name: {user.full_name}")
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check authorization
    if not is_authorized(update):
        await update.message.reply_text(f"⛔ Unauthorized. Your ID is: {update.effective_user.id}")
        return

    await update.message.reply_text("I'm ready to chat.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.channel_post
    if not message:
        return

    # --- AUTHORIZATION CHECK ---
    if not is_authorized(update):
        await message.reply_text(f"⛔ Permission denied. Your ID: {update.effective_user.id}")
        return

    user_text = message.text
    chat_type = message.chat.type
    bot_username = context.bot.username

    # --- DECISION LOGIC ---
    should_reply = False
    if chat_type == 'private':
        should_reply = True
    else:
        # In groups, reply if mentioned OR if replying to the bot
        if user_text and f"@{bot_username}" in user_text:
            should_reply = True
            user_text = user_text.replace(f"@{bot_username}", "").strip()
        
        if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            should_reply = True

    if not should_reply:
        return

    # --- SEND TO API ---
    await context.bot.send_chat_action(chat_id=message.chat.id, action=constants.ChatAction.TYPING)

    try:
        # INCREASED TIMEOUT to 120 seconds
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "message": user_text
            }
            
            response = await client.post(API_URL, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                raw_reply = data.get("response", "...")
                
                final_reply = clean_response(raw_reply)
                
                if not final_reply:
                    final_reply = "..."

                await message.reply_text(final_reply)
            else:
                logging.error(f"API Error: {response.status_code}")
                await message.reply_text("My brain returned an error.")

    except httpx.ReadTimeout:
        logging.error("LLM Generation Timed Out")
        await message.reply_text("I'm thinking too hard... try again later.")
        
    except Exception as e:
        logging.error(f"Connection Error: {e}")
        await message.reply_text("I can't reach the server.")

def run_bot():
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN env variable not set.")
        return

    print("Starting Bot...")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    
    msg_filter = filters.TEXT & (~filters.COMMAND)
    application.add_handler(MessageHandler(msg_filter, handle_message))

    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    run_bot()
