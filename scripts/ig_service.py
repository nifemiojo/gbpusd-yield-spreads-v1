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

        print("IG Client initialized.")

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

        self.cst = response.headers.get("CST")
        self.x_security_token = response.headers.get("X-SECURITY-TOKEN")
        self.last_login = time.time()
        self._update_headers()

        print("Logged in successfully.")

    def refresh_session(self):
        """Keep the session alive."""
        self._update_headers()

        response = self.session.put(f"{self.base_url}/session")

        response.raise_for_status()

        if response.status_code == 200:
            print("Session refreshed.")
            self.last_login = time.time()
        else:
            print("Session refresh failed, re-logging in.")
            print(response.text)
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
    
    def close_position(self, inner_position_object):
        body = {
            "dealId": inner_position_object["dealId"],
            "direction": "BUY" if inner_position_object["direction"] == "SELL" else "SELL",
            "size": inner_position_object["size"],
            "orderType": "MARKET"
        }

        response = self.request("DELETE", f"/positions/otc", version="2", data=json.dumps(body))

        if response.status_code == 200:
            print("Close request accepted.")
            return response.json()
        else:
            print(f"Failed to close position ({response.status_code}): {response.text}")
            return None

    def place_market_order(self, direction, size):
        payload = {
            "epic": "CS.D.GBPUSD.TODAY.IP",
            "direction": direction,
            "orderType": "MARKET",
            "size": size,
            "currencyCode": "GBP",
            "expiry": "-",
            "forceOpen": False,
            "guaranteedStop": False
        }

        return self.request("POST", "/positions/otc", version="2", data=json.dumps(payload)).json()
    
    # Return price object: e.g. {'bid': 13172.8, 'ask': 13173.7, 'lastTraded': None}
    def get_current_price(self):
        response = self.request("GET", "/prices/CS.D.GBPUSD.TODAY.IP", version="3").json()
        return sorted(response["prices"], key=lambda x: x["snapshotTime"], reverse=True)[0]["closePrice"]
    
    def logout(self):
        response = self.request("DELETE", "/session")

        response.raise_for_status()
        print("Logged out successfully.")

        self.session.close()

        return response