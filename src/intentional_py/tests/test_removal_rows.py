"""Tests for '-'/'--' removal rows: marking an intent (or one of its languages)
for removal instead of building it. See models.ConfigRow, validate.check_rows,
and build_intents._remove_marked_intents.
"""

from pathlib import Path

import pytest

from intentional_py import build_intents, exceptions, models, validate
from intentional_py.tests.conftest import FakeReporter, dd_project


def test_double_dash_removal_is_confirmed_without_asking() -> None:
    row = models.ConfigRow.from_csv_row(
        ["--A.Pay", "Ctx", "en", "pay", "", "", ""], row_number=1
    )

    assert row.intent == "A.Pay"
    assert row.removal is True
    assert row.remove_confirmed is True
    assert row.ok


def test_single_dash_removal_needs_confirmation() -> None:
    row = models.ConfigRow.from_csv_row(
        ["-A.Pay", "Ctx", "en", "pay", "", "", ""], row_number=1
    )

    assert row.intent == "A.Pay"
    assert row.removal is True
    assert row.remove_confirmed is False


def test_three_or_more_dashes_are_treated_as_a_double_dash() -> None:
    row = models.ConfigRow.from_csv_row(
        ["---A.Pay", "Ctx", "en", "pay", "", "", ""], row_number=1
    )

    assert row.intent == "A.Pay"
    assert row.removal is True
    assert row.remove_confirmed is True
    assert row.ok


def test_removal_row_still_validates_the_stripped_name() -> None:
    # only the leading '-' is a removal marker; a '-' anywhere else in the name
    # is still the usual forbidden-character rule
    row = models.ConfigRow.from_csv_row(
        ["-A-Bad", "Ctx", "en", "pay", "", "", ""], row_number=1
    )

    assert row.removal is True
    assert row.errors == ["Row 1: intent name 'A-Bad' cannot contain '-'."]


def test_check_rows_excludes_removal_rows_from_build_rows(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    config.write_text("A.Pay,Ctx,en,pay,,,\n--A.Old,Ctx,en,old,,,\n", encoding="utf-8")

    rows, errors, _warnings, removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert errors == []
    assert [row[0] for row in rows] == ["A.Pay"]
    assert len(removals) == 1
    assert removals[0].intent == "A.Old"
    assert removals[0].language == "en"
    assert removals[0].confirmed is True


def test_check_rows_warns_when_default_language_removal_leaves_other_languages(
    tmp_path: Path,
) -> None:
    config = tmp_path / "intents.cfg"
    config.write_text("--A.Old,Ctx,en,old,,,\nA.Old,Ctx,es,old,,,\n", encoding="utf-8")

    _rows, _errors, warnings, _removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert any(
        "'A.Old'" in warning and "es" in warning and "not marked for removal" in warning
        for warning in warnings
    )


def test_check_rows_does_not_warn_about_its_own_default_language(
    tmp_path: Path,
) -> None:
    # a duplicate default-language row (the phrase-swap feature) alongside the removal
    # row for the same intent/language shouldn't produce a nonsensical "removing 'en'
    # also removes its en files" warning - only an *other* language should trigger it
    config = tmp_path / "intents.cfg"
    config.write_text("A.Old,Ctx,en,old,,,\n--A.Old,Ctx,en,old2,,,\n", encoding="utf-8")

    _rows, _errors, warnings, _removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert not any("also removes its" in warning for warning in warnings)


def test_check_rows_deduplicates_conflicting_dash_and_double_dash_rows(
    tmp_path: Path,
) -> None:
    # the same intent+language marked for removal twice, once with '-' and once with
    # '--': should collapse to a single RemovalRow, confirmed (since '--' is there)
    config = tmp_path / "intents.cfg"
    config.write_text("-A.Old,Ctx,en,old,,,\n--A.Old,Ctx,en,old,,,\n", encoding="utf-8")

    _rows, _errors, _warnings, removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert len(removals) == 1
    assert removals[0].confirmed is True


def test_check_rows_removal_alone_does_not_synthesize_a_build_row(
    tmp_path: Path,
) -> None:
    # a lone 'es' removal row for an intent shouldn't invent a brand new 'en' build
    # row for it, unlike a normal 'es' build row (see the default-language synthesis)
    config = tmp_path / "intents.cfg"
    config.write_text("-A.Old,Ctx,es,old,,,\n", encoding="utf-8")

    rows, _errors, warnings, removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert rows == []
    assert not any("synthesized" in warning for warning in warnings)
    assert len(removals) == 1


def test_build_force_removes_an_intent_without_confirmation(tmp_path: Path) -> None:
    config = dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    reporter = FakeReporter()
    build_intents.intents("DD", config, tmp_path, reporter)

    config.write_text("--A.Pay,Ctx,en,pay,,,\n", encoding="utf-8")
    phrase_dir = tmp_path / "Training Phrases" / "en"
    phrase_dir.mkdir(parents=True, exist_ok=True)
    (phrase_dir / "pay.txt").write_text("pay my bill\n", encoding="utf-8")

    result = build_intents.intents("DD", config, tmp_path, reporter)

    assert reporter.questions == []  # '--' never asks
    assert sorted(result.removed) == ["A.Pay.json", "A.Pay_usersays_en.json"]
    assert not (tmp_path / "intents" / "A.Pay.json").exists()
    assert not (tmp_path / "intents" / "A.Pay_usersays_en.json").exists()


def test_build_asks_before_removing_with_a_single_dash(tmp_path: Path) -> None:
    config = dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    build_intents.intents("DD", config, tmp_path, FakeReporter())

    config.write_text("-A.Pay,Ctx,en,pay,,,\n", encoding="utf-8")
    reporter = FakeReporter(answer=True)

    result = build_intents.intents("DD", config, tmp_path, reporter)

    assert reporter.questions == ["Remove the intents marked for removal"]
    assert "A.Pay.json" in result.removed


def test_build_aborts_when_removal_is_declined(tmp_path: Path) -> None:
    config = dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    build_intents.intents("DD", config, tmp_path, FakeReporter())

    config.write_text("-A.Pay,Ctx,en,pay,,,\n", encoding="utf-8")

    with pytest.raises(exceptions.IntentionalException):
        build_intents.intents("DD", config, tmp_path, FakeReporter(answer=False))

    # nothing was removed, and nothing new was written either
    assert (tmp_path / "intents" / "A.Pay.json").exists()


def test_build_removes_only_the_named_language_when_not_the_default(
    tmp_path: Path,
) -> None:
    config = dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    es_dir = tmp_path / "Training Phrases" / "es"
    es_dir.mkdir(parents=True)
    (es_dir / "pay.txt").write_text("pagar mi factura\n", encoding="utf-8")
    config.write_text(
        config.read_text(encoding="utf-8") + "A.Pay,Ctx,es,pay,,,\n", encoding="utf-8"
    )
    build_intents.intents("DD", config, tmp_path, FakeReporter())
    assert (tmp_path / "intents" / "A.Pay_usersays_es.json").exists()

    config.write_text("A.Pay,Ctx,en,pay,,,\n--A.Pay,Ctx,es,pay,,,\n", encoding="utf-8")

    result = build_intents.intents("DD", config, tmp_path, FakeReporter())

    assert result.removed == ["A.Pay_usersays_es.json"]
    assert (tmp_path / "intents" / "A.Pay.json").exists()
    assert (tmp_path / "intents" / "A.Pay_usersays_en.json").exists()
    assert not (tmp_path / "intents" / "A.Pay_usersays_es.json").exists()


def test_validate_reports_a_pending_removal(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    config.write_text("-A.Old,Ctx,en,old,,,\n", encoding="utf-8")

    class NullReporter:
        def message(self, level, text):
            pass

    result = validate.validate(config, tmp_path, NullReporter())

    check = result.configs[0]
    # a removal-only config isn't "empty" - nothing says the config has no data
    assert check.ok
    assert not any("does not contain data" in detail for detail in check.details)
    assert any("marked for removal" in detail for detail in check.details)
    assert any("will ask for confirmation first" in detail for detail in check.details)
