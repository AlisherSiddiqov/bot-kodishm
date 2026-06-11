import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMINS = {855774248}
CHANNELS = [ "@Asalarichlikni"]  # guruh username ni yozing

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env ichida yo'q.")