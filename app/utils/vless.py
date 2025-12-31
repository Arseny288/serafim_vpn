# app/utils/vless.py
from app.config import Config

def build_vless_link(vpn_uuid: str, email: str, cfg=Config) -> str:
    return (
        f"vless://{vpn_uuid}@{cfg.SERVER_IP}:{cfg.SERVER_PORT}"
        f"?security=reality&encryption=none"
        f"&pbk={cfg.PUBLIC_KEY}"
        f"&fp=chrome&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"&sni={cfg.SNI}&sid={cfg.SHORT_ID}"
        f"#{email}"
    )
