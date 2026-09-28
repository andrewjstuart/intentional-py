"""Custom exception classes for intentional-py."""


class IntentionalException(Exception):
    """Base exception class for all intentional-py errors."""


class ConfigurationError(IntentionalException):
    """Raised when there is an error in configuration file or settings."""


class ValidationError(IntentionalException):
    """Raised when validation of data fails."""


class ExtractionError(IntentionalException):
    """Raised when there is an error during Excel file extraction."""


class IntentBuildError(IntentionalException):
    """Raised when there is an error building intents."""


class FileSystemError(IntentionalException):
    """Raised when there is an error accessing the file system."""
