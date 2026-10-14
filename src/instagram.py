"""Thin client for the official Instagram API (Instagram Login, graph.instagram.com).

Needs a Business or Creator account and a long-lived access token with
the instagram_business_basic, instagram_business_content_publish and
instagram_business_manage_insights permissions. No passwords involved.
"""
import os
import time

import requests

API = "https://graph.instagram.com"
VER = os.environ.get("IG_API_VERSION", "v23.0")


class IG:
    def __init__(self, token=None, user_id=None):
        self.token = token or os.environ["IG_ACCESS_TOKEN"]
        self.user_id = user_id or os.environ.get("IG_USER_ID") or self.me()["user_id"]

    def _get(self, path, **params):
        params["access_token"] = self.token
        r = requests.get(f"{API}/{VER}/{path}", params=params, timeout=60)
        if not r.ok:
            raise RuntimeError(f"GET {path} failed: {r.status_code} {r.text}")
        return r.json()

    def _post(self, path, **data):
        data["access_token"] = self.token
        r = requests.post(f"{API}/{VER}/{path}", data=data, timeout=60)
        if not r.ok:
            raise RuntimeError(f"POST {path} failed: {r.status_code} {r.text}")
        return r.json()

    def me(self):
        return self._get("me", fields="user_id,username")

    # ---- publishing ----
    def publish_image(self, image_url, caption):
        container = self._post(f"{self.user_id}/media", image_url=image_url, caption=caption)["id"]
        for _ in range(30):  # wait until Instagram has fetched/processed the image
            status = self._get(container, fields="status_code").get("status_code")
            if status == "FINISHED":
                break
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Container {container} status {status}")
            time.sleep(5)
        media_id = self._post(f"{self.user_id}/media_publish", creation_id=container)["id"]
        return media_id

    def publishing_limit(self):
        return self._get(f"{self.user_id}/content_publishing_limit", fields="quota_usage,config")

    # ---- insights ----
    def recent_media(self, limit=30):
        return self._get(f"{self.user_id}/media",
                         fields="id,caption,timestamp,permalink,like_count,comments_count",
                         limit=limit).get("data", [])

    def media_insights(self, media_id):
        try:
            data = self._get(f"{media_id}/insights",
                             metric="reach,views,saved,shares,total_interactions").get("data", [])
        except RuntimeError as e:
            print(f"[insights] {media_id}: {e}")
            return {}
        return {m["name"]: m["values"][0]["value"] for m in data}

    def account_insights(self, period_days=7):
        until = int(time.time())
        since = until - period_days * 86400
        try:
            data = self._get(f"{self.user_id}/insights", metric="reach,follower_count",
                             period="day", since=since, until=until).get("data", [])
        except RuntimeError as e:
            print(f"[insights] account: {e}")
            return {}
        return {m["name"]: sum(v["value"] for v in m.get("values", [])) for m in data}

    # ---- token ----
    @staticmethod
    def refresh_token(token):
        r = requests.get(f"{API}/refresh_access_token",
                         params={"grant_type": "ig_refresh_token", "access_token": token},
                         timeout=60)
        if not r.ok:
            raise RuntimeError(f"Token refresh failed: {r.status_code} {r.text}")
        return r.json()  # {"access_token", "token_type", "expires_in"}
