"""Tests for password complexity validator.

The validator enforces: 8+ chars, uppercase, lowercase, digit, special char.
"""

import pytest

from app.schemas.auth import _validate_password


class TestPasswordComplexity:
    def test_valid_password(self):
        assert _validate_password("SecureP@ss1") == "SecureP@ss1"

    def test_valid_with_all_special_chars(self):
        assert _validate_password("Test!@#1abc") == "Test!@#1abc"

    def test_too_short(self):
        with pytest.raises(ValueError, match="at least 8 characters"):
            _validate_password("Sh@1abc")

    def test_no_uppercase(self):
        with pytest.raises(ValueError, match="uppercase"):
            _validate_password("lowercase@1")

    def test_no_lowercase(self):
        with pytest.raises(ValueError, match="lowercase"):
            _validate_password("UPPERCASE@1")

    def test_no_digit(self):
        with pytest.raises(ValueError, match="uppercase"):
            _validate_password("NoDigit@abc")

    def test_no_special_char(self):
        with pytest.raises(ValueError, match="uppercase"):
            _validate_password("NoSpecial1abc")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            _validate_password("")

    def test_exactly_8_chars_valid(self):
        assert _validate_password("Abcdef1!") == "Abcdef1!"

    def test_7_chars_too_short(self):
        with pytest.raises(ValueError, match="at least 8 characters"):
            _validate_password("Abcde1!")

    def test_long_password_valid(self):
        assert _validate_password("A" * 50 + "b1!") == "A" * 50 + "b1!"

    def test_space_not_special_enough(self):
        """Space is not in the special char set."""
        with pytest.raises(ValueError):
            _validate_password("NoSpecial1abc")

    def test_underscore_is_special(self):
        assert _validate_password("Test_Password1") == "Test_Password1"

    def test_dash_is_special(self):
        assert _validate_password("Test-Password1") == "Test-Password1"
