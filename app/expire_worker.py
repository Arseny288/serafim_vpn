# app/services/expire_worker.py
import asyncio
from datetime import datetime

async def expire_worker(users, xui, config):
    while True:
        expired = await users.get_expired_active()
        for u in expired:
            xui.update_client(
                config.INBOUND_ID,
                u.vpn_uuid,
                enable=False,
                expiry_ms=int(u.active_until.timestamp() * 1000)
            )
            await users.set_active(u.user_id, False)
        await asyncio.sleep(60)
