class CarunaError(Exception):
    """Base error for Caruna+ requests."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class CarunaAuthError(CarunaError):
    """Login failed or the session is no longer valid."""


class CarunaApiError(CarunaError):
    """A Caruna+ API request failed."""
