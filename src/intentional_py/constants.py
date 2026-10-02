"""Constants and configuration values for intentional-py."""

# Supported languages and their codes; overridable per user (see models.LanguageSettings
# and user_settings.py) - these are just the original hardcoded default, not every
# language Dialogflow ES supports. See ALL_DIALOGFLOW_LANGUAGES below for the full catalog
# to add from.
VALID_LANGUAGES = {"en", "es", "fr"}
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
}
DEFAULT_LANGUAGE = "en"

# Every language Dialogflow ES supports, for 'language-settings --add CODE' to look up a
# display name from (see docs/future-features.md's "Configurable supported language set").
# Not the active default (LANGUAGE_NAMES above is, to keep existing projects unchanged) -
# this is a reference catalog only. Regional variants (e.g. 'en-us', 'fr-ca') collapse to
# the bare language code, except where Dialogflow only offers a regional one (e.g. Chinese,
# Portuguese).
ALL_DIALOGFLOW_LANGUAGES = {
    "af": "Afrikaans",
    "sq": "Albanian",
    "am": "Amharic",
    "hy": "Armenian",
    "az": "Azerbaijani",
    "eu": "Basque",
    "be": "Belarusian",
    "bn": "Bengali",
    "bs": "Bosnian",
    "bg": "Bulgarian",
    "ca": "Catalan",
    "ceb": "Cebuano",
    "ny": "Chichewa",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "co": "Corsican",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "eo": "Esperanto",
    "et": "Estonian",
    "fil": "Filipino",
    "fi": "Finnish",
    "fr": "French",
    "fy": "Frisian",
    "gl": "Galician",
    "ka": "Georgian",
    "de": "German",
    "el": "Greek",
    "gu": "Gujarati",
    "ht": "Haitian Creole",
    "ha": "Hausa",
    "hi": "Hindi",
    "hmn": "Hmong",
    "hu": "Hungarian",
    "is": "Icelandic",
    "ig": "Igbo",
    "id": "Indonesian",
    "ga": "Irish",
    "it": "Italian",
    "ja": "Japanese",
    "jv": "Javanese",
    "kn": "Kannada",
    "kk": "Kazakh",
    "km": "Khmer",
    "rw": "Kinyarwanda",
    "ko": "Korean",
    "ku": "Kurdish",
    "ky": "Kyrgyz",
    "la": "Latin",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "lb": "Luxembourgish",
    "mk": "Macedonian",
    "mg": "Malagasy",
    "ms": "Malay",
    "ml": "Malayalam",
    "mt": "Maltese",
    "mi": "Maori",
    "mr": "Marathi",
    "mn": "Mongolian",
    "ne": "Nepali",
    "no": "Norwegian",
    "or": "Oriya/Odia",
    "pl": "Polish",
    "pt-br": "Portuguese (Brazil)",
    "pt": "Portuguese (Portugal)",
    "pa": "Punjabi",
    "ro": "Romanian",
    "ru": "Russian",
    "sm": "Samoan",
    "gd": "Scots Gaelic",
    "sr": "Serbian",
    "st": "Sesotho",
    "sn": "Shona",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "so": "Somali",
    "es": "Spanish",
    "su": "Sundanese",
    "sw": "Swahili",
    "sv": "Swedish",
    "tg": "Tajik",
    "ta": "Tamil",
    "tt": "Tatar",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "tk": "Turkmen",
    "uk": "Ukrainian",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "cy": "Welsh",
    "xh": "Xhosa",
    "yo": "Yoruba",
    "zu": "Zulu",
}

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
DEFAULT_NL_SUBFOLDER = "NL"

# File extensions
SUPPORTED_EXCEL_EXTENSIONS = {".xlsb", ".xlsm", ".xlsx"}
PHRASE_FILE_EXTENSION = ".txt"
INTENT_FILE_EXTENSION = ".json"

# Configuration file defaults
DEFAULT_DD_CONFIG = "intents.cfg"
DEFAULT_NL_CONFIG = "intents_nl.cfg"

# Default NL context
DEFAULT_NL_CONTEXT = "GetIntent"
