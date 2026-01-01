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
            print(f"XUI login failed: status={r.status_code}, response={r.text}")
            return False
        try:
            response_json = r.json()
            success = bool(response_json.get("success"))
            if not success:
                print(f"XUI login failed: response={response_json}")
            return success
        except Exception as e:
            print(f"XUI login exception: {e}, response={r.text}")
            return False

    def get_inbound(self, inbound_id: int) -> dict | None:
        """Get inbound settings by ID"""
        url = f"{self.base_url}/panel/api/inbounds/get/{inbound_id}"
        r = self.session.get(url, timeout=10)
        if r.status_code != 200:
            print(f"XUI get_inbound failed: status={r.status_code}, response={r.text}")
            return None
        try:
            response_json = r.json()
            if response_json.get("success"):
                return response_json.get("obj")
            return None
        except Exception as e:
            print(f"XUI get_inbound exception: {e}, response={r.text}")
            return None

    def update_inbound(self, inbound_id: int, settings: dict) -> bool:
        """Update entire inbound settings"""
        url = f"{self.base_url}/panel/api/inbounds/update/{inbound_id}"
        # Include id in payload as some XUI versions require it
        payload = {"id": inbound_id, "settings": json.dumps(settings)}
        r = self.session.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"XUI update_inbound failed: status={r.status_code}, response={r.text}")
            return False
        try:
            response_json = r.json()
            success = bool(response_json.get("success"))
            if not success:
                print(f"XUI update_inbound failed: response={response_json}")
            return success
        except Exception as e:
            print(f"XUI update_inbound exception: {e}, response={r.text}")
            return False

    def add_client(self, inbound_id: int, client: dict) -> bool:
        # First try the simple addClient endpoint
        url = f"{self.base_url}/panel/api/inbounds/addClient"
        payload = {"id": inbound_id, "settings": json.dumps({"clients": [client]})}
        r = self.session.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            try:
                response_json = r.json()
                if response_json.get("success"):
                    return True
            except Exception:
                pass
        
        # If addClient fails, try getting the inbound and updating it with all clients
        print(f"XUI addClient direct failed, trying get+update approach...")
        inbound = self.get_inbound(inbound_id)
        if not inbound:
            print(f"XUI add_client failed: could not get inbound {inbound_id}")
            return False
        
        # Parse existing clients from inbound settings
        try:
            settings_str = inbound.get("settings", "{}")
            if isinstance(settings_str, str):
                settings = json.loads(settings_str)
            else:
                settings = settings_str
            
            existing_clients = settings.get("clients", [])
            
            # Ensure all existing clients have an email field to avoid SQL errors
            # If email is missing or None, generate one based on UUID
            for c in existing_clients:
                if not c.get("email"):
                    # Generate email from UUID if available, otherwise use a default
                    client_id = c.get("id", "")
                    if client_id:
                        c["email"] = f"client_{client_id[:8]}"
                    else:
                        c["email"] = "client_unknown"
            
            # Add our new client
            existing_clients.append(client)
            settings["clients"] = existing_clients
            
            # Update the inbound with all clients
            return self.update_inbound(inbound_id, settings)
            
        except Exception as e:
            print(f"XUI add_client exception parsing inbound: {e}")
            return False

    def update_client(self, inbound_id: int, uuid_str: str, enable: bool, expiry_ms: int) -> bool:
        """
        В 3x-ui обычно есть:
        POST /panel/api/inbounds/updateClient/{uuid}
        body: {"id": inbound_id, "settings": "..."} либо отдельные поля.
        Но у разных форков эндпоинты отличаются.

        Самый "живучий" способ — использовать updateClient/{uuid} с settings clients[0].
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
            print(f"XUI update_client failed: status={r.status_code}, response={r.text}")
            return False
        try:
            response_json = r.json()
            success = bool(response_json.get("success"))
            if not success:
                print(f"XUI update_client failed: response={response_json}")
            return success
        except Exception as e:
            print(f"XUI update_client exception: {e}, response={r.text}")
            return False