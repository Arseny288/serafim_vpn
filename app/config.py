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
@dataclass(frozen=True)
class XuiConfig:
    url: str
    username: str
    password: str
    inbound_id: int
    server_ip: str
    server_port: int
    public_key: str
    sni: str
    short_id: str

def load_xui_config() -> XuiConfig:
    return XuiConfig(
        url=os.getenv("XUI_URL", "http://localhost:8080").strip(),
        username=os.getenv("XUI_USER", "").strip(),
        password=os.getenv("XUI_PASS", "").strip(),
        inbound_id=int(os.getenv("XUI_INBOUND_ID", "2")),
        server_ip=os.getenv("SERVER_IP", "").strip(),
        server_port=int(os.getenv("SERVER_PORT", "443")),
        public_key=os.getenv("PUBLIC_KEY", "").strip(),
        sni=os.getenv("SNI", "google.com").strip(),
        short_id=os.getenv("SHORT_ID", "").strip(),
    )

# Backward compatibility - deprecated, use load_xui_config() instead
class Config:
    _cached_config = None
    
    @classmethod
    def _get_config(cls):
        if cls._cached_config is None:
            cls._cached_config = load_xui_config()
        return cls._cached_config
    
    @classmethod
    def XUI_URL(cls):
        return cls._get_config().url
    
    @classmethod
    def XUI_USER(cls):
        return cls._get_config().username
    
    @classmethod
    def XUI_PASS(cls):
        return cls._get_config().password
    
    @classmethod
    def INBOUND_ID(cls):
        return cls._get_config().inbound_id
    
    @classmethod
    def SERVER_IP(cls):
        return cls._get_config().server_ip
    
    @classmethod
    def SERVER_PORT(cls):
        return cls._get_config().server_port
    
    @classmethod
    def PUBLIC_KEY(cls):
        return cls._get_config().public_key
    
    @classmethod
    def SNI(cls):
        return cls._get_config().sni
    
    @classmethod
    def SHORT_ID(cls):
        return cls._get_config().short_id
