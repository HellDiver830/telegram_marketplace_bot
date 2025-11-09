import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "telegram_bot")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")


raw_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [int(x) for x in raw_admins.split(",") if x.strip().isdigit()]
