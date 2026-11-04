"""Exception type carrying an HTTP status and a user-facing message."""


class ApiError(Exception):
    """Raised by any handler to return a clean JSON error to the browser."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message
