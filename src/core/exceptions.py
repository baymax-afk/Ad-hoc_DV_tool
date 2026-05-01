class DVToolError(Exception):
    """Base exception for all domain errors."""


class IngestionError(DVToolError):
    pass


class UnderstandingError(DVToolError):
    pass


class IntentError(DVToolError):
    pass


class RenderingError(DVToolError):
    pass


class SessionNotFoundError(DVToolError):
    pass


class UnsupportedChartError(DVToolError):
    pass
