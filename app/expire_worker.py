# app/expire_worker.py
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def expire_worker(users, xui, config):
    """Background worker that disables expired subscriptions"""
    while True:
        try:
            expired = await users.get_expired_active()
            for u in expired:
                try:
                    if not xui.login():
                        logger.error(f"XUI login failed when disabling expired user {u.user_id}")
                        continue
                    
                    expiry_ms = int(u.active_until.timestamp() * 1000) if u.active_until else 0
                    ok = xui.update_client(config.INBOUND_ID, u.vpn_uuid, False, expiry_ms)
                    if not ok:
                        logger.error(f"Failed to disable client for expired user {u.user_id}")
                    else:
                        await users.set_active(u.user_id, False)
                        logger.info(f"Disabled expired subscription for user {u.user_id}")
                except Exception as e:
                    logger.error(f"Error processing expired user {u.user_id}: {e}")
            
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in expire_worker: {e}")
            await asyncio.sleep(60)
