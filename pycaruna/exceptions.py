class CarunaError(Exception):
    """Base error for Caruna+ requests."""


class CarunaAuthError(CarunaError):
    """Login failed or the session is no longer valid."""


class CarunaApiError(CarunaError):
    """A Caruna+ API request failed."""
