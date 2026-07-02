import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

CLICK_CARD = os.getenv("CLICK_CARD", "8600 XXXX XXXX XXXX")
PAYME_CARD = os.getenv("PAYME_CARD", "8600 XXXX XXXX XXXX")
CARD_OWNER = os.getenv("CARD_OWNER", "F.I.Sh.")

DB_PATH = os.getenv("DB_PATH", "donatbot.sqlite3")

# Mini App'ning o'zi joylashgan ochiq (https) manzil, masalan https://donat.onrender.com
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# Render kabi platformalar PORT'ni o'zi beradi
PORT = int(os.getenv("PORT", "8000"))

# Admin veb-panel uchun login/parol
ADMIN_PANEL_USERNAME = os.getenv("ADMIN_PANEL_USERNAME", "admin")
ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "changeme123")
