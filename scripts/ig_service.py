import os
from dotenv import load_dotenv
import requests
import json
import time

class IGClient:
    def __init__(self):
        load_dotenv()

        self.username = os.getenv("IG_USERNAME")
        self.password = os.getenv("IG_PASSWORD")
        self.base_url = os.getenv("IG_BASE_URL")
        self.api_key = os.getenv("IG_API_KEY")

        self.session = requests.Session()

        self.cst = None
        self.x_security_token = None
        self.last_login = None

        self.login()

    def _update_headers(self):
        self.session.headers.update({
            "X-IG-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        if self.cst and self.x_security_token:
            self.session.headers.update({
                "CST": self.cst,
                "X-SECURITY-TOKEN": self.x_security_token,
            })

    def login(self):
        payload = {
            "identifier": self.username,
            "password": self.password,
        }

        self._update_headers()

        response = self.session.post(
            f"{self.base_url}/session",
            headers={"Version": "2"},
            data=json.dumps(payload)
        )

        print(response.status_code, response.text, response.headers)

        self.cst = response.headers.get("CST")
        self.x_security_token = response.headers.get("X-SECURITY-TOKEN")
        self.last_login = time.time()
        self._update_headers()

        print("Logged in successfully.")
        print(self.session.headers)

    def refresh_session(self):
        """Keep the session alive."""
        self._update_headers()

        response = self.session.put(f"{self.base_url}/session")

        if response.status_code == 200:
            print("Session refreshed.")
            self.last_login = time.time()
        else:
            print("Session refresh failed, re-logging in.")
            self.login()

    def _auto_refresh_if_needed(self, max_age=3600):
        """Auto-refresh every hour or on expiry."""
        if time.time() - self.last_login > max_age:
            self.refresh_session()

    def request(self, method, endpoint, version="1", **kwargs):
        """Generic method for GET/POST/PUT/DELETE with auto-refresh."""
        self._auto_refresh_if_needed()
        url = f"{self.base_url}{endpoint}"
        request_sepcific_headers = {
            "Version": version
        }

        response = self.session.request(method, url, headers=request_sepcific_headers, **kwargs)

        # Retry if session expired
        if response.status_code in (401, 403):
            print("Session expired — logging in again..." + response.text)
            self.login()
            response = self.session.request(method, url, **kwargs)

        return response
    
    def get_accounts(self):
        return self.request("GET", "/accounts").json()
    
    def get_positions(self):
        return self.request("GET", "/positions", version="2").json()
    
    def logout(self):
        response =self.request("DELETE", "/session").json()

        self.session.close()
        print("Logged out successfully.")

        return response