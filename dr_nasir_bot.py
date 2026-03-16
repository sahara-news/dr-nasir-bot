
import os
import logging
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("GEMINI_API_KEY environment variable not set. Exiting.")
    exit(1)

# Initialize Gemini model with system instruction
GEMINI_MODEL = "gemini-2.0-flash" # Changed to gemini-2.0-flash as requested
SYSTEM_INSTRUCTION = "Tumhara naam Dr. Nasir hai. Tum ek helpful AI assistant ho. Tum hamesha Roman Urdu (Urdu written in English/Latin script) mein reply karte ho. Tum friendly aur professional ho."

# For models that support system instructions
model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_INSTRUCTION)

# Health check server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running and healthy!")

def run_health_server():
    port = int(os.environ.get("PORT", 8080)) # Default to 8080 if PORT not set
    server_address = ("", port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Health check server running on port {port}")
    httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! Main Dr. Nasir hoon. Kaise ho aap? Mujhse kuch bhi pooch sakte ho."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Aap mujhse koi bhi sawal Roman Urdu mein pooch sakte ho.")

async def generate_gemini_reply(user_message: str) -> str:
    """Generate a reply using Google Gemini API."""
    try:
        # Start a chat session without system prompt in history, as it's already in model config
        chat = model.start_chat(history=[])
        response = await chat.send_message_async(user_message)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating reply from Gemini: {e}", exc_info=True) # Log full traceback
        return "Maaf karna, abhi main jawab nahi de pa raha. Kuch masla ho gaya hai."

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message with Gemini-generated reply."""
    user_message = update.message.text
    if not user_message:
        return

    logger.info(f"Received message from {update.effective_user.full_name}: {user_message}")
    reply_text = await generate_gemini_reply(user_message)
    await update.message.reply_text(reply_text)
    logger.info(f"Sent reply to {update.effective_user.full_name}: {reply_text}")

def main() -> None:
    """Start the bot and the health check server."""
    # Start the health check server in a separate thread FIRST
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True  # Allow the main program to exit even if thread is running
    health_thread.start()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # On non command i.e. message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
