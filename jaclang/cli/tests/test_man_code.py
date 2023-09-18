"""Test Jac cli module."""
import io
import sys

from jaclang.cli import cmds
from jaclang.utils.test import TestCase


class JacCliTests(TestCase):
    """Test pass module."""

    def setUp(self) -> None:
        """Set up test."""
        return super().setUp()

    def test_circle_jac(self) -> None:
        """Basic test for pass."""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        # Execute the function
        cmds.run(self.fixture_abs_path("../../../../examples/manual_code/circle.jac"))  # type: ignore

        sys.stdout = sys.__stdout__
        stdout_value = captured_output.getvalue()

        # Assertions or verifications
        self.assertEqual(
            "Area of a circle with radius 5 using function: 78.53981633974483\n"
            "Area of a Circle with radius 5 using class: 78.53981633974483\n",
            stdout_value,
        )