from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_id: int
    db_dsn: str
    monthly_price_rub: int
    warning_days: int

    @property
    def daily_price(self) -> float:
        return round(self.monthly_price_rub / 30, 2)

def load_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        db_dsn=os.getenv("DB_DSN", "sqlite+aiosqlite:///vpn_bot.db").strip(),
        monthly_price_rub=int(os.getenv("MONTHLY_PRICE_RUB", "150")),
        warning_days=int(os.getenv("WARNING_DAYS", "3")),
    )
# app/config.py
class Config:
    XUI_URL = "http://79.137.197.188:8080"
    XUI_USER = "paneladmin"
    XUI_PASS = "mSETja7tD369"

    INBOUND_ID = 2

    SERVER_IP = "79.137.197.188"
    SERVER_PORT = 443
    PUBLIC_KEY = "kN5gCvgOrDm2ku-pyHMxeOoMH0hT3OkV-JX8a-pl3DI"
    SNI = "google.com"
    SHORT_ID = "7c"
