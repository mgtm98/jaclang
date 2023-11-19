"""Tests for Jac Workspace."""
import os

from jaclang.jac.workspace import Workspace
from jaclang.utils.test import TestCase


class TestWorkspace(TestCase):
    """Test Jac Workspace."""

    def test_workspace_basic(self) -> None:
        """Basic test of functionarlity."""
        ws = Workspace(path=os.path.join(os.path.dirname(__file__)))
        self.assertGreater(len(ws.modules.keys()), 4)

    def test_dependecies_basic(self) -> None:
        """Basic test of functionarlity."""
        ws = Workspace(path=os.path.join(os.path.dirname(__file__)))
        key = [i for i in ws.modules.keys() if "fam.jac" in i][0]
        self.assertGreater(len(ws.get_dependencies(key)), 0)

    def test_symbols_basic(self) -> None:
        """Basic test of functionarlity."""
        ws = Workspace(path=os.path.join(os.path.dirname(__file__)))
        key = [i for i in ws.modules.keys() if "fam.jac" in i][0]
        self.assertGreater(len(ws.get_symbols(key)), 5)

    def test_get_defs_basic(self) -> None:
        """Basic test of functionarlity."""
        ws = Workspace(path=os.path.join(os.path.dirname(__file__)))
        key = [i for i in ws.modules.keys() if "fam.jac" in i][0]
        self.assertGreater(len(ws.get_definitions(key)), 5)

    def test_get_uses_basic(self) -> None:
        """Basic test of functionarlity."""
        ws = Workspace(path=os.path.join(os.path.dirname(__file__)))
        key = [i for i in ws.modules.keys() if "fam.jac" in i][0]
        self.assertGreater(len(ws.get_uses(key)), 5)

    def test_man_code_dir(self) -> None:
        """Test of circle workspace."""
        loc = os.path.join(os.path.dirname(__file__))
        # print(loc)
        ws = Workspace(path=loc + "/../../../examples/manual_code")
        key = [i for i in ws.modules.keys() if "circle.jac" in i][0]
        # for i in ws.get_uses(key):
        #     print(i.pp())
        # print(ws.get_uses(key))
        self.assertGreater(len(ws.get_uses(key)), 5)
