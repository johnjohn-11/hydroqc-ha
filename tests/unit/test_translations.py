"""The translation files stay in step with each other and with the config flow."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from custom_components.hydroqc.config_flow.helpers import RATE_CODE_MAPPING, rate_key

COMPONENT = Path(__file__).parents[2] / "custom_components" / "hydroqc"
LANGUAGES = ("en", "fr", "es")


def _keys(data: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        if isinstance(value, dict):
            keys |= _keys(value, f"{prefix}{key}.")
        else:
            keys.add(f"{prefix}{key}")
    return keys


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def test_strings_json_is_the_english_translation() -> None:
    """strings.json and translations/en.json hold the same content."""
    assert _load(COMPONENT / "strings.json") == _load(COMPONENT / "translations" / "en.json")


@pytest.mark.parametrize("language", LANGUAGES)
def test_translation_has_the_keys_of_strings_json(language: str) -> None:
    """Every language has exactly the keys of strings.json."""
    reference = _keys(_load(COMPONENT / "strings.json"))
    assert _keys(_load(COMPONENT / "translations" / f"{language}.json")) == reference


def test_every_config_flow_step_is_translated() -> None:
    """Each step shown by the config flow has a title in strings.json."""
    strings = _load(COMPONENT / "strings.json")
    source = (COMPONENT / "config_flow" / "base.py").read_text(encoding="utf-8")
    steps = set(re.findall(r'step_id="(\w+)"', source))
    assert steps
    assert steps <= set(strings["config"]["step"])


def test_every_offered_rate_is_translated() -> None:
    """Each rate the OpenData flow can offer has a label."""
    options = _load(COMPONENT / "strings.json")["selector"]["rate_selection"]["options"]
    assert {rate_key(*offer) for offer in RATE_CODE_MAPPING.values()} == set(options)
