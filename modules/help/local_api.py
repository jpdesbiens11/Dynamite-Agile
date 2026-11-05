"""In-process API calls (D-B-024), used at start-up to fill the DEMO
learning project through the very same handlers, validations and audit log
as a user in the browser -- without an HTTP server or a password.
"""
from core.errors import ApiError


class LocalApi:
    def __init__(self, ctx):
        self.ctx = ctx  # core.startup.StartupContext: conn, user (an administrator), data_dir

    def call(self, method, path, body=None, query=None):
        from core import router  # local import: router imports every module
        for route_method, pattern, handler, _access in router.ROUTES:
            match = pattern.fullmatch(path)
            if match and route_method == method:
                self.ctx.body = body or {}
                self.ctx.params = match.groupdict()
                self.ctx.query = query or {}
                return handler(self.ctx)
        raise ApiError(404, "Route locale introuvable : {} {}".format(method, path))

    def get(self, path, query=None):
        return self.call("GET", path, query=query)

    def post(self, path, body=None):
        return self.call("POST", path, body)

    def put(self, path, body=None):
        return self.call("PUT", path, body)

    def patch(self, path, body=None):
        return self.call("PATCH", path, body)
