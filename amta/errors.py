"""AMTA domain exceptions."""


class AmtaError(Exception):
    """Base exception for AMTA errors."""


class AmtaConfigError(AmtaError):
    """Raised when AMTA workspace configuration is invalid."""


class AmtaParseError(AmtaError):
    """Raised when a node file cannot be parsed."""


class AmtaValidationError(AmtaError):
    """Raised when AMTA validation fails."""


class AmtaBuildError(AmtaError):
    """Raised when artifact generation fails."""
