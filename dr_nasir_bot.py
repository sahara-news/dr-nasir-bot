import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set. Exiting.")
    exit(1)

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY environment variable not set. Exiting.")
    exit(1)

# Initialize Groq client (OpenAI compatible)
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = "Tumhara naam Dr. Nasir hai. Tum ek helpful AI assistant ho. Tum hamesha Roman Urdu (Urdu written in English/Latin script) mein reply karte ho. Tum friendly aur professional ho."


# Health check server - responds to ALL paths with 200 OK
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass  # Suppress health check logs


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('', port)
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
    await update.message.reply_text("Aap mujhse koi bhi sawal pooch sakte ho. Main Roman Urdu mein jawab dunga.")


async def generate_reply(user_message: str) -> str:
    """Generate a reply using Groq API."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating reply from Groq: {e}", exc_info=True)
        return "Maaf karna, abhi main jawab nahi de pa raha. Kuch masla ho gaya hai."


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages with AI-generated reply."""
    user_message = update.message.text
    if not user_message:
        return

    logger.info(f"Received message from {update.effective_user.full_name}: {user_message}")
    reply_text = await generate_reply(user_message)
    await update.message.reply_text(reply_text)
    logger.info(f"Sent reply to {update.effective_user.full_name}: {reply_text}")


def main() -> None:
    """Start the bot and the health check server."""
    # Start the health check server FIRST in a separate thread
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True
    health_thread.start()

    # Create the Application and pass it your bot's token
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
