import pytest

from intentional_py import constants, models


def test_valid_row_parses_context_entities_and_priority() -> None:
    row = models.ConfigRow.from_csv_row(
        [
            "MYAC.NewServiceHomeOrBus.Home{high}",
            "Ctx-A|Ctx-B",
            "en",
            "home",
            "digits4[last_4]|sys.date*",
            "1",
            "FALSE",
        ],
        row_number=1,
    )

    assert row.intent == "MYAC.NewServiceHomeOrBus.Home"
    assert row.priority == 750000
    assert row.contexts == ["Ctx-A", "Ctx-B"]
    assert row.dtmf == ["1"]
    assert row.machine_learning is False
    assert row.machine_learning_text == "false"
    assert row.entities == [
        models.Entity(
            type="@digits4",
            name="last_4",
            value="$last_4",
            required=False,
            aliased=True,
        ),
        models.Entity(
            type="@sys.date", name="date", value="$date", required=True, aliased=False
        ),
    ]
    assert row.ok
    assert row.errors == []
    assert row.warnings == []
    assert row.context_text == "Ctx-A|Ctx-B"


def test_entity_parse_marks_an_aliased_entity_as_required() -> None:
    # a trailing * after the closing bracket applies to the whole reference, alias included
    assert models.Entity.parse("sys.phone-number[phone]*") == models.Entity(
        type="@sys.phone-number",
        name="phone",
        value="$phone",
        required=True,
        aliased=True,
    )
    assert models.Entity.parse("sys.phone-number[phone]") == models.Entity(
        type="@sys.phone-number",
        name="phone",
        value="$phone",
        required=False,
        aliased=True,
    )


def test_entity_to_config_text_round_trips_through_parse() -> None:
    for text in [
        "sys.date",
        "sys.date*",
        "digits4",
        "digits4[last_4]",
        "sys.phone-number[phone]*",
    ]:
        entity = models.Entity.parse(text)
        assert entity.to_config_text() == text
        assert models.Entity.parse(entity.to_config_text()) == entity


def test_blank_machine_learning_defaults_to_true_without_a_warning() -> None:
    row = models.ConfigRow.from_csv_row(
        ["A.Pay", "Ctx", "en", "pay", "", ""], row_number=1
    )

    assert row.machine_learning is True
    assert row.machine_learning_text == "TRUE"
    assert row.warnings == []


def test_missing_intent_is_a_row_prefixed_error_but_still_parses() -> None:
    # like check_rows(), a fatal problem on one field doesn't stop the rest of the row
    # from being read; the whole build aborts separately once any row has an error
    row = models.ConfigRow.from_csv_row(
        ["", "Ctx", "en", "pay", "", "", ""], row_number=3
    )

    assert not row.ok
    assert row.errors == ["Row 3: intent name is required."]
    assert row.action == "pay"


def test_intent_with_dash_is_an_error() -> None:
    row = models.ConfigRow.from_csv_row(
        ["A-Pay", "Ctx", "en", "pay", "", "", ""], row_number=1
    )

    assert row.errors == ["Row 1: intent name 'A-Pay' cannot contain '-'."]


def test_context_with_a_dot_is_a_warning_not_an_error() -> None:
    row = models.ConfigRow.from_csv_row(
        ["A.Pay", "Get.Intent", "en", "pay", "", "", ""], row_number=1
    )

    assert row.ok
    assert row.warnings == ["Row 1: context 'Get.Intent' contains '.'."]


def test_custom_naming_rules_can_relax_the_default_intent_and_context_checks() -> None:
    rules = models.NamingRules(intent_forbidden_chars="", context_discouraged_chars="")
    row = models.ConfigRow.from_csv_row(
        ["A-Pay", "Get.Intent", "en", "pay", "", "", ""], row_number=1, rules=rules
    )

    assert row.ok
    assert row.warnings == []


def test_custom_naming_rules_can_add_a_different_forbidden_character() -> None:
    rules = models.NamingRules(intent_forbidden_chars="_")
    row = models.ConfigRow.from_csv_row(
        ["A_Pay", "Ctx", "en", "pay", "", "", ""], row_number=1, rules=rules
    )

    assert row.errors == ["Row 1: intent name 'A_Pay' cannot contain '_'."]

    # the original '-' rule no longer applies, since it was replaced rather than added to
    allowed = models.ConfigRow.from_csv_row(
        ["A-Pay", "Ctx", "en", "pay", "", "", ""], row_number=1, rules=rules
    )
    assert allowed.ok


def test_intent_path_separator_is_an_error_even_with_relaxed_rules() -> None:
    # unconditional: the intent name becomes a file name, so this can't be relaxed via
    # NamingRules the way the '-' convention can (a real safety rule, not a team convention)
    rules = models.NamingRules(intent_forbidden_chars="")
    row = models.ConfigRow.from_csv_row(
        ["../../evil", "Ctx", "en", "pay", "", "", ""], row_number=1, rules=rules
    )

    assert row.errors == ["Row 1: intent name '../../evil' cannot contain '/' or '\\'."]


def test_project_layout_defaults_match_the_original_hardcoded_layout() -> None:
    layout = models.ProjectLayout()

    assert layout.training_phrases_dir == constants.DEFAULT_TRAINING_PHRASES_DIR
    assert layout.intents_dir == constants.DEFAULT_INTENTS_DIR
    assert layout.nl_subfolder == constants.DEFAULT_NL_SUBFOLDER
    assert layout.dd_config == constants.DEFAULT_DD_CONFIG
    assert layout.nl_config == constants.DEFAULT_NL_CONFIG


def test_project_layout_fields_can_be_overridden() -> None:
    layout = models.ProjectLayout(
        training_phrases_dir="Phrases",
        intents_dir="output",
        nl_subfolder="natural-language",
        dd_config="dd.cfg",
        nl_config="nl.cfg",
    )

    assert layout.training_phrases_dir == "Phrases"
    assert layout.intents_dir == "output"
    assert layout.nl_subfolder == "natural-language"
    assert layout.dd_config == "dd.cfg"
    assert layout.nl_config == "nl.cfg"


def test_nl_defaults_default_matches_the_original_hardcoded_context() -> None:
    assert models.NlDefaults().context == constants.DEFAULT_NL_CONTEXT


def test_nl_defaults_context_can_be_overridden() -> None:
    assert models.NlDefaults(context="MainContext").context == "MainContext"


def test_language_settings_defaults_match_the_original_hardcoded_set() -> None:
    languages = models.LanguageSettings()

    assert languages.languages == constants.LANGUAGE_NAMES
    assert languages.default_language == constants.DEFAULT_LANGUAGE
    assert languages.codes == constants.VALID_LANGUAGES


def test_language_settings_can_be_overridden() -> None:
    languages = models.LanguageSettings(
        languages={"en": "English", "de": "German"}, default_language="de"
    )

    assert languages.codes == {"en", "de"}
    assert languages.default_language == "de"


def test_config_row_accepts_a_custom_language_set() -> None:
    languages = models.LanguageSettings(
        languages={"en": "English", "de": "German"}, default_language="de"
    )

    row = models.ConfigRow.from_csv_row(
        ["A.Pay", "Ctx", "de", "pay", "", "", ""], row_number=1, languages=languages
    )

    assert row.ok
    assert row.language == "de"


def test_config_row_rejects_a_language_outside_the_custom_set() -> None:
    languages = models.LanguageSettings(
        languages={"en": "English", "de": "German"}, default_language="de"
    )

    row = models.ConfigRow.from_csv_row(
        ["A.Pay", "Ctx", "fr", "pay", "", "", ""], row_number=1, languages=languages
    )

    assert row.language == "de"
    assert row.warnings == ["Row 1: language 'fr' will default to 'de'."]


def test_action_with_a_path_separator_is_an_error() -> None:
    # unconditional: the action is used to find a phrase file
    row = models.ConfigRow.from_csv_row(
        ["A.Pay", "Ctx", "en", "../../etc/passwd", "", "", ""], row_number=1
    )

    assert row.errors == [
        "Row 1: action '../../etc/passwd' cannot contain '/' or '\\'."
    ]


def test_dtmf_row_without_a_value_is_an_error() -> None:
    row = models.ConfigRow.from_csv_row(
        ["A.Menu", "Ctx", "dtmf", "menu", "", "", ""], row_number=1
    )

    assert row.errors == ["Row 1: DTMF rows require a DTMF value."]


def test_invalid_dtmf_characters_are_an_error() -> None:
    # DTMF is a hardware/platform constraint (0-9, '#', '*'), not this project's own
    # convention, so unlike the intent/context naming rules it is not configurable
    row = models.ConfigRow.from_csv_row(
        ["A.Menu", "Ctx", "en", "menu", "", "1|x", ""], row_number=4
    )

    assert row.errors == ["Row 4: invalid DTMF values ['x']; must be 0-9, '#' or '*'."]


def test_invalid_language_is_a_warning_not_an_error() -> None:
    row = models.ConfigRow.from_csv_row(
        ["A.Pay", "Ctx", "xx", "pay", "", "", ""], row_number=2
    )

    assert row.ok
    assert row.language == "en"
    assert row.warnings == ["Row 2: language 'xx' will default to 'en'."]


def test_invalid_machine_learning_value_is_a_warning_not_an_error() -> None:
    row = models.ConfigRow.from_csv_row(
        ["A.Pay", "Ctx", "en", "pay", "", "", "maybe"], row_number=5
    )

    assert row.ok
    assert row.machine_learning is True
    assert row.machine_learning_text == "TRUE"
    assert row.warnings == [
        "Row 5: machine learning value 'maybe' will default to 'TRUE'."
    ]


def test_wrong_column_count_raises_since_the_row_cannot_be_read_at_all() -> None:
    with pytest.raises(ValueError, match=r"^Row 1: expected 6 or 7 values, found 3\.$"):
        models.ConfigRow.from_csv_row(["A.Pay", "Ctx", "en"], row_number=1)


def test_parse_rows_mirrors_check_rows_return_shape() -> None:
    rows, errors, warnings = models.parse_rows(
        [
            ["A.Pay", "Ctx", "en", "pay", "", "", ""],
            ["", "Ctx", "en", "pay", "", "", ""],
            ["A.Menu", "Ctx", "zz", "menu", "", "", ""],
        ]
    )

    # check_rows() keeps every row it can read, even ones with their own errors
    assert [row.intent for row in rows] == ["A.Pay", "", "A.Menu"]
    assert errors == ["Row 2: intent name is required."]
    assert warnings == ["Row 3: language 'zz' will default to 'en'."]


def test_parse_rows_reports_wrong_column_count_and_skips_the_row() -> None:
    rows, errors, warnings = models.parse_rows(
        [["A.Pay", "Ctx", "en", "pay", "", "", ""], ["A.Bad", "Ctx"]]
    )

    assert [row.intent for row in rows] == ["A.Pay"]
    assert errors == ["Row 2: expected 6 or 7 values, found 2."]
    assert warnings == []
