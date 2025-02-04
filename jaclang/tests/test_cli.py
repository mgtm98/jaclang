"""Test Jac cli module."""
import io
import subprocess
import sys


from jaclang.cli import cli
from jaclang.utils.test import TestCase


class JacCliTests(TestCase):
    """Test pass module."""

    def setUp(self) -> None:
        """Set up test."""
        return super().setUp()

    def test_jac_cli_run(self) -> None:
        """Basic test for pass."""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        # Execute the function
        cli.run(self.fixture_abs_path("hello.jac"))  # type: ignore

        sys.stdout = sys.__stdout__
        stdout_value = captured_output.getvalue()

        self.assertIn("Hello World!", stdout_value)

    def test_jac_cli_alert_based_err(self) -> None:
        """Basic test for pass."""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        sys.stderr = captured_output

        # Execute the function
        # try:
        cli.enter(self.fixture_abs_path("err2.jac"), entrypoint="speak", args=[])  # type: ignore
        # except Exception as e:
        #     print(f"Error: {e}")

        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        stdout_value = captured_output.getvalue()
        # print(stdout_value)
        self.assertIn("Errors occurred", stdout_value)

    def test_jac_ast_tool_pass_template(self) -> None:
        """Basic test for pass."""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        cli.ast_tool("pass_template")

        sys.stdout = sys.__stdout__
        stdout_value = captured_output.getvalue()
        self.assertIn("Sub objects.", stdout_value)
        self.assertGreater(stdout_value.count("def exit_"), 10)

    def test_jac_cmd_line(self) -> None:
        """Basic test for pass."""
        process = subprocess.Popen(
            ["jac"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout_value, _ = process.communicate(input="exit\n")
        self.assertEqual(process.returncode, 0, "Process did not exit successfully")
        self.assertIn("Welcome to the Jac CLI!", stdout_value)

    def test_ast_print(self) -> None:
        """Testing for print AstTool."""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        cli.ast_tool("print", [f"{self.fixture_abs_path('hello.jac')}"])

        sys.stdout = sys.__stdout__
        stdout_value = captured_output.getvalue()
        self.assertIn("+-- Token", stdout_value)

    def test_ast_dotgen(self) -> None:
        """Testing for print AstTool."""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        cli.ast_tool("dot_gen", [f"{self.fixture_abs_path('hello.jac')}"])

        sys.stdout = sys.__stdout__
        stdout_value = captured_output.getvalue()
        self.assertIn('[label="MultiString"]', stdout_value)

    def test_type_check(self) -> None:
        """Testing for print AstTool."""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        cli.type_check(f"{self.fixture_abs_path('game1.jac')}")
        sys.stdout = sys.__stdout__
        stdout_value = captured_output.getvalue()
        self.assertIn(
            'Argument 2 to "is_pressed" of "Button" has incompatible type "tuple[bool, bool, bool]"; expected "str"',
            stdout_value,
        )
