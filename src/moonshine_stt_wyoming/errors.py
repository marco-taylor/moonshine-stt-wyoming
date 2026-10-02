class ServiceError(Exception):
    """Safe, fixed diagnostic suitable for returning to clients."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ConfigurationError(ValueError):
    """Invalid configuration. Never includes untrusted values."""
