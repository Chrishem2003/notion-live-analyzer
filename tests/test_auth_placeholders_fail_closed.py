"""Regression tests for placeholder authentication modules that must fail closed."""
from __future__ import annotations

import importlib


class StopRendering(Exception):
    pass


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.messages = []

    def error(self, message):
        self.messages.append(("error", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def stop(self):
        raise StopRendering()


def test_demo_auth_gateway_never_authenticates(monkeypatch):
    module = importlib.import_module("auth")
    fake = FakeStreamlit()
    monkeypatch.setattr(module, "st", fake)

    try:
        module.render_auth_gateway()
    except StopRendering:
        pass
    else:
        raise AssertionError("placeholder gateway must stop rendering")

    assert fake.session_state.get("authenticated") is not True
    assert any(level == "error" for level, _ in fake.messages)


def test_shared_totp_vault_demo_never_unlocks(monkeypatch):
    module = importlib.import_module("vault_auth")
    fake = FakeStreamlit()
    monkeypatch.setattr(module, "st", fake)

    try:
        module.render_secure_vault_auth()
    except StopRendering:
        pass
    else:
        raise AssertionError("vault demo must stop rendering")

    assert fake.session_state.get("vault_unlocked") is not True
    assert any(level == "error" for level, _ in fake.messages)
