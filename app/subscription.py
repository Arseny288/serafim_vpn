# app/services/subscription.py
from datetime import datetime, timedelta
import uuid

class SubscriptionService:
    def __init__(self, users, xui, config):
        self.users = users
        self.xui = xui
        self.cfg = config

    async def activate(self, tg_id: int, days: int):
        u = await self.users.get(tg_id)
        if not u:
            return

        if not u.vpn_uuid:
            vpn_uuid = str(uuid.uuid4())
            email = f"tg_{tg_id}"

            expires = datetime.utcnow() + timedelta(days=days)
            expiry_ms = int(expires.timestamp() * 1000)

            client = {
                "id": vpn_uuid,
                "email": email,
                "flow": "xtls-rprx-vision",
                "limitIp": 1,  # 🔥 ТОЛЬКО 1 УСТРОЙСТВО
                "totalGB": 0,
                "expiryTime": expiry_ms,
                "enable": True
            }

            self.xui.add_client(self.cfg.INBOUND_ID, client)
            await self.users.set_vpn(tg_id, vpn_uuid, email, expires)
        else:
            expiry_ms = int((u.active_until + timedelta(days=days)).timestamp() * 1000)
            self.xui.update_client(self.cfg.INBOUND_ID, u.vpn_uuid, True, expiry_ms)
            await self.users.extend_until(tg_id, days)

    async def pause(self, tg_id: int):
        u = await self.users.get(tg_id)
        if not u or not u.vpn_uuid:
            return
        self.xui.update_client(
            self.cfg.INBOUND_ID,
            u.vpn_uuid,
            enable=False,
            expiry_ms=int(u.active_until.timestamp() * 1000)
        )
        await self.users.set_active(tg_id, False)
