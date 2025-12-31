import json
import requests


class XuiPanel:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()

    def login(self) -> bool:
        url = f"{self.base_url}/login"
        r = self.session.post(url, data={"username": self.username, "password": self.password}, timeout=10)
        if r.status_code != 200:
            return False
        try:
            return bool(r.json().get("success"))
        except Exception:
            return False

    def add_client(self, inbound_id: int, client: dict) -> bool:
        url = f"{self.base_url}/panel/api/inbounds/addClient"
        payload = {"id": inbound_id, "settings": json.dumps({"clients": [client]})}
        r = self.session.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            return False
        try:
            return bool(r.json().get("success"))
        except Exception:
            return False

    def update_client(self, inbound_id: int, uuid_str: str, enable: bool, expiry_ms: int) -> bool:
        """
        В 3x-ui обычно есть:
        POST /panel/api/inbounds/updateClient/{uuid}
        body: {"id": inbound_id, "settings": "..."} либо отдельные поля.
        Но у разных форков эндпоинты отличаются.

        Самый “живучий” способ — использовать updateClient/{uuid} с settings clients[0].
        """
        url = f"{self.base_url}/panel/api/inbounds/updateClient/{uuid_str}"

        client = {
            "id": uuid_str,
            "enable": enable,
            "expiryTime": expiry_ms,
        }

        payload = {"id": inbound_id, "settings": json.dumps({"clients": [client]})}

        r = self.session.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            return False
        try:
            return bool(r.json().get("success"))
        except Exception:
            return False
