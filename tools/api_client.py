"""Tiny HTTP client for the platform API (standard library only).

Used by the end-to-end tests and by tools/seed_demo.py. Keeps the session
cookie and sends the CSRF token on every write, like the browser does.
"""
import http.cookiejar
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request


class ApiFailure(Exception):
    def __init__(self, status, message):
        super().__init__("{} {}".format(status, message))
        self.status = status
        self.message = message


class Client:
    def __init__(self, base_url, cafile=None):
        """`cafile`: CA that signed the server certificate, for an https:// URL (development CA, D-B-091)."""
        self.base = base_url.rstrip("/")
        self.csrf = None
        jar = http.cookiejar.CookieJar()
        handlers = [urllib.request.HTTPCookieProcessor(jar)]
        if cafile:
            handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(cafile))))
        self.opener = urllib.request.build_opener(*handlers)

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if method != "GET" and self.csrf:
            request.add_header("X-CSRF-Token", self.csrf)
        try:
            with self.opener.open(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8")
            try:
                message = json.loads(text).get("error", text)
            except ValueError:
                message = text
            raise ApiFailure(exc.code, message)
        if isinstance(payload, dict) and "csrf" in payload:
            self.csrf = payload["csrf"]
        return payload

    def get(self, path):
        return self.call("GET", path)

    def post(self, path, body=None):
        return self.call("POST", path, body or {})

    def patch(self, path, body):
        return self.call("PATCH", path, body)

    def put(self, path, body):
        return self.call("PUT", path, body)

    def delete(self, path):
        return self.call("DELETE", path)

    def upload(self, path, data, content_type="application/octet-stream", filename=""):
        """POST raw bytes to a file-upload route (core lot v0.4)."""
        request = urllib.request.Request(self.base + path, data=data, method="POST")
        request.add_header("Content-Type", content_type)
        request.add_header("X-File-Name", urllib.parse.quote(filename))
        if self.csrf:
            request.add_header("X-CSRF-Token", self.csrf)
        try:
            with self.opener.open(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8")
            try:
                message = json.loads(text).get("error", text)
            except ValueError:
                message = text
            raise ApiFailure(exc.code, message)

    def raw_get(self, path):
        """GET a file; returns (status, headers, bytes) without raising."""
        try:
            with self.opener.open(self.base + path, timeout=15) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def login(self, username, password, new_password=None):
        me = self.post("/api/login", {"username": username, "password": password})
        if me["user"]["must_change_password"] and new_password:
            me = self.post("/api/me/password", {"old_password": password, "new_password": new_password})
        return me
