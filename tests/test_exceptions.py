"""Tests for DeskPulse custom exceptions."""

import pytest
from app.core.exceptions import DeskPulseException


class TestDeskPulseException:
    """Tests for base exception class."""

    def test_exception_can_be_raised(self):
        """Verify DeskPulseException can be raised and caught."""
        with pytest.raises(DeskPulseException):
            raise DeskPulseException("Test error message")

    def test_exception_message(self):
        """Verify exception stores message correctly."""
        msg = "Something went wrong"
        exc = DeskPulseException(msg)
        assert str(exc) == msg

    def test_exception_inherits_from_exception(self):
        """Verify DeskPulseException inherits from Exception."""
        assert issubclass(DeskPulseException, Exception)

    def test_exception_caught_as_exception(self):
        """Verify DeskPulseException can be caught as generic Exception."""
        with pytest.raises(Exception):
            raise DeskPulseException("Caught as Exception")
