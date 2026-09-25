"""Constants and configuration values for intentional-py."""

# Supported languages and their codes
VALID_LANGUAGES = {"en", "es", "fr"}
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
}
DEFAULT_LANGUAGE = "en"

# Supported modes for processing
VALID_MODES = {"DD", "NL"}
DEFAULT_MODE = "DD"

# DTMF (Dual-Tone Multi-Frequency) valid values
VALID_DTMF_VALUES = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "#", "*"}

# Priority mapping for intent processing
PRIORITY_MAP = {
    "1": 1000000,
    "2": 750000,
    "3": 500000,  # default to "normal" priority
    "4": 250000,
    "5": -1,
    "highest": 1000000,
    "high": 750000,
    "normal": 500000,
    "low": 250000,
    "ignore": -1,
}
DEFAULT_PRIORITY = 500000

# Machine learning settings
MACHINE_LEARNING_DEFAULT = "TRUE"
VALID_ML_VALUES = {"true", "false"}

# Directory structure
DEFAULT_TRAINING_PHRASES_DIR = "Training Phrases"
DEFAULT_INTENTS_DIR = "intents"

# File extensions
SUPPORTED_EXCEL_EXTENSIONS = {".xlsb", ".xlsm", ".xlsx"}
PHRASE_FILE_EXTENSION = ".txt"
INTENT_FILE_EXTENSION = ".json"

# Configuration file defaults
DEFAULT_DD_CONFIG = "intents.cfg"
DEFAULT_NL_CONFIG = "intents_nl.cfg"

# Default NL context
DEFAULT_NL_CONTEXT = "GetIntent"
