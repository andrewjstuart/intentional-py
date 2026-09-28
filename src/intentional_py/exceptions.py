"""Custom exception classes for intentional-py."""


class IntentionalException(Exception):
    """Base exception class for all intentional-py errors."""

    pass


class ConfigurationError(IntentionalException):
    """Raised when there is an error in configuration file or settings."""

    pass


class ValidationError(IntentionalException):
    """Raised when validation of data fails."""

    pass


class ExtractionError(IntentionalException):
    """Raised when there is an error during Excel file extraction."""

    pass


class IntentBuildError(IntentionalException):
    """Raised when there is an error building intents."""

    pass


class FileSystemError(IntentionalException):
    """Raised when there is an error accessing the file system."""

    pass
