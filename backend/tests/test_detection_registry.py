"""Tests for detection engine registry pattern.

Verifies that:
1. All built-in checkers are registered
2. Custom checkers can be registered
3. get_checker returns correct classes
4. Unregistered rule types return None
"""

from datetime import datetime, timezone

import pytest

from app.services.detection import (
    RuleChecker,
    _CHECKER_REGISTRY,
    get_checker,
    register_checker,
)


def test_builtin_checkers_registered():
    """All built-in rule types should be registered at import time."""
    expected = [
        "failed_logins",
        "brute_force",
        "high_cpu",
        "high_memory",
        "high_disk",
        "service_failure",
        "agent_offline",
    ]
    for rule_type in expected:
        assert rule_type in _CHECKER_REGISTRY, f"{rule_type} not registered"


def test_get_checker_returns_instance():
    checker = get_checker("failed_logins")
    assert checker is not None
    assert isinstance(checker, RuleChecker)


def test_get_checker_unknown_returns_none():
    assert get_checker("nonexistent_rule") is None


def test_register_custom_checker():
    """A custom checker can be registered and retrieved."""
    class CustomChecker(RuleChecker):
        rule_type = "custom_test_rule"
        description = "Test rule"

        async def check(self, db, host, rule, now):
            return None

    register_checker(CustomChecker)
    try:
        checker = get_checker("custom_test_rule")
        assert isinstance(checker, CustomChecker)
    finally:
        _CHECKER_REGISTRY.pop("custom_test_rule", None)


def test_checker_registry_is_dict():
    """Registry is a plain dict mapping rule_type -> checker instance."""
    assert isinstance(_CHECKER_REGISTRY, dict)
    for key, val in _CHECKER_REGISTRY.items():
        assert isinstance(key, str)
        assert isinstance(val, RuleChecker)


def test_all_checkers_have_required_attrs():
    """Every registered checker must have rule_type and description."""
    for rule_type, checker_cls in _CHECKER_REGISTRY.items():
        assert checker_cls.rule_type == rule_type, f"Mismatch for {rule_type}"
        assert isinstance(checker_cls.description, str)
        assert len(checker_cls.description) > 0


def test_checkers_are_instances():
    """Every registered checker is an instance with correct rule_type."""
    for rule_type, checker in _CHECKER_REGISTRY.items():
        assert isinstance(checker, RuleChecker)
        assert checker.rule_type == rule_type
