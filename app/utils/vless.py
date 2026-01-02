# app/utils/vless.py
from app.config import XuiConfig

def build_vless_link(vpn_uuid: str, email: str, cfg: XuiConfig) -> str:
    return (
        f"vless://{vpn_uuid}@{cfg.server_ip}:{cfg.server_port}"
        f"?security=reality&encryption=none"
        f"&pbk={cfg.public_key}"
        f"&fp=chrome&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"&sni={cfg.sni}&sid={cfg.short_id}"
        f"#{email}"
    )
