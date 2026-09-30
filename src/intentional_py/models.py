"""A typed model of one config row, used by validate.check_rows() for the per-row rules.

ConfigRow.from_csv_row() mirrors check_rows()'s per-row checks exactly (same fatal vs.
warning split, same message text), so check_rows() can call it instead of checking each
field by hand. It never raises for a domain rule: like check_rows(), it collects every
problem so all of them can be shown at once, and normalizes what it safely can (language,
machine learning). The checks that need more than one row (duplicate phrases, intents
sharing an intent+language pair, the synthesized English row) or the filesystem (phrase
files) are not part of a single row and stay in validate.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from intentional_py import constants, utils


class Entity(BaseModel):
    """One entity reference in the Entities column, e.g. sys.phone-number[phone]."""

    type: str
    name: str
    value: str
    required: bool = False
    aliased: bool = (
        False  # True when [alias] was present, so to_config_text() can round-trip it
    )

    @classmethod
    def parse(cls, text: str) -> Entity:
        entity_type, name, value, required = utils.check_alias(text)
        return cls(
            type=entity_type,
            name=name,
            value=value,
            required=required,
            aliased="[" in text,
        )

    def to_config_text(self) -> str:
        """The Entities column text for this one entity, e.g. sys.phone-number[phone]*."""
        type_text = self.type.removeprefix("@")
        star = "*" if self.required else ""
        return (
            f"{type_text}[{self.name}]{star}" if self.aliased else f"{type_text}{star}"
        )


class NamingRules(BaseModel):
    """Intent/context naming rules, overridable per user; these defaults match the original
    hardcoded behavior. Not Dialogflow requirements, just this project's naming convention,
    so a user can relax them for a project with different standards (see user_settings.py).
    """

    intent_forbidden_chars: str = (
        "-"  # any of these chars in an intent name is a fatal error
    )
    context_discouraged_chars: str = "."  # any of these chars in a context is a warning


class ConfigRow(BaseModel):
    """One row of intents.cfg / intents_nl.cfg, and the problems found while reading it."""

    intent: str
    priority: int = constants.DEFAULT_PRIORITY
    contexts: list[str] = Field(default_factory=list)
    context_text: str = (
        ""  # the raw Context cell, unsplit; JSON only has room for one context value
    )
    language: str = constants.DEFAULT_LANGUAGE
    action: str
    entities: list[Entity] = Field(default_factory=list)
    dtmf: list[str] = Field(default_factory=list)
    machine_learning: bool = True
    machine_learning_text: str = constants.MACHINE_LEARNING_DEFAULT
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @classmethod
    def from_csv_row(
        cls, row: list[str], row_number: int, rules: NamingRules | None = None
    ) -> ConfigRow:
        """Build from a raw 6- or 7-value config line, collecting problems instead of raising.

        rules (NamingRules | None): intent/context naming rules; defaults to NamingRules()
            (the original hardcoded behavior) when not given.
        """
        if len(row) not in (6, 7):
            raise ValueError(
                f"Row {row_number}: expected 6 or 7 values, found {len(row)}."
            )
        rules = rules or NamingRules()
        cells = [cell.strip() for cell in row] + [""] * (7 - len(row))
        (
            intent_text,
            context_text,
            language_text,
            action_text,
            entities_text,
            dtmf_text,
            ml_text,
        ) = cells

        errors: list[str] = []
        warnings: list[str] = []

        if not intent_text:
            errors.append(f"Row {row_number}: intent name is required.")
        elif "/" in intent_text or "\\" in intent_text:
            # unconditional, not part of NamingRules: the intent name becomes a file name,
            # so a path separator could write a file outside the intents folder
            errors.append(
                f"Row {row_number}: intent name '{intent_text}' cannot contain '/' or '\\'."
            )
        else:
            found = sorted(
                {c for c in rules.intent_forbidden_chars if c in intent_text}
            )
            if found:
                chars = "', '".join(found)
                errors.append(
                    f"Row {row_number}: intent name '{intent_text}' cannot contain '{chars}'."
                )

        if not context_text:
            errors.append(f"Row {row_number}: context is required.")
        else:
            found = sorted(
                {c for c in rules.context_discouraged_chars if c in context_text}
            )
            if found:
                chars = "', '".join(found)
                warnings.append(
                    f"Row {row_number}: context '{context_text}' contains '{chars}'."
                )

        if not action_text:
            errors.append(f"Row {row_number}: action is required.")
        elif "/" in action_text or "\\" in action_text:
            # unconditional: the action is used to find a phrase file, so a path separator
            # could read a file outside the Training Phrases folder
            errors.append(
                f"Row {row_number}: action '{action_text}' cannot contain '/' or '\\'."
            )

        language = language_text.lower()
        if language not in constants.VALID_LANGUAGES | {"dtmf"}:
            warnings.append(
                f"Row {row_number}: language '{language or '<blank>'}' "
                f"will default to '{constants.DEFAULT_LANGUAGE}'."
            )
            language = constants.DEFAULT_LANGUAGE

        if language == "dtmf" and not dtmf_text:
            errors.append(f"Row {row_number}: DTMF rows require a DTMF value.")

        dtmf = [part for part in dtmf_text.split("|") if part]
        invalid_dtmf = set(dtmf) - constants.VALID_DTMF_VALUES
        if invalid_dtmf:
            errors.append(
                f"Row {row_number}: invalid DTMF values {sorted(invalid_dtmf)}; "
                "must be 0-9, '#' or '*'."
            )

        if not ml_text:
            machine_learning_text = constants.MACHINE_LEARNING_DEFAULT
        elif ml_text.lower() not in constants.VALID_ML_VALUES:
            machine_learning_text = constants.MACHINE_LEARNING_DEFAULT
            warnings.append(
                f"Row {row_number}: machine learning value '{ml_text}' "
                f"will default to '{constants.MACHINE_LEARNING_DEFAULT}'."
            )
        else:
            machine_learning_text = ml_text.lower()

        intent, priority = utils.check_priority(intent_text)
        return cls(
            intent=intent,
            priority=priority,
            contexts=[part for part in context_text.split("|") if part],
            context_text=context_text,
            language=language,
            action=action_text,
            entities=[Entity.parse(part) for part in entities_text.split("|") if part],
            dtmf=dtmf,
            machine_learning=machine_learning_text.lower() == "true",
            machine_learning_text=machine_learning_text,
            errors=errors,
            warnings=warnings,
        )


def parse_rows(rows: list[list[str]]) -> tuple[list[ConfigRow], list[str], list[str]]:
    """Mirrors check_rows()'s (rows, errors, warnings) return shape, for comparison."""
    parsed_rows: list[ConfigRow] = []
    errors: list[str] = []
    warnings: list[str] = []
    for row_number, row in enumerate(rows, start=1):
        try:
            parsed_row = ConfigRow.from_csv_row(row, row_number)
        except ValueError as error:
            errors.append(str(error))
            continue
        parsed_rows.append(parsed_row)
        errors.extend(parsed_row.errors)
        warnings.extend(parsed_row.warnings)
    return parsed_rows, errors, warnings
