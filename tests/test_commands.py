import pytest

import commands  # noqa: F401  регистрирует команды
from core import handle_command, registry


def test_commands_registered():
    assert len(registry.commands) > 50


def test_no_duplicate_function_names_per_pattern_set():
    for cmd in registry.commands:
        assert cmd["patterns"], cmd["name"]


@pytest.mark.parametrize("phrase", ["привет", "как дела", "спасибо"])
def test_small_talk_returns_text(phrase):
    assert handle_command(phrase, source="test")


def test_time_mentions_digits():
    assert any(ch.isdigit() for ch in handle_command("время", source="test"))
