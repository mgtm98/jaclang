"""Jac Blue pass for Jaseci Ast.

At the end of this pass a meta['py_code'] is present with pure python code
in each node. Module nodes contain the entire module code.
"""
import jaclang.jac.absyntree as ast
from jaclang.jac.constant import Constants as Con
from jaclang.jac.constant import Tokens as Tok
from jaclang.jac.passes import Pass


class BluePygenPass(Pass):
    """Jac blue transpilation to python pass."""

    def before_pass(self) -> None:
        """Initialize pass."""
        self.indent_size = 4
        self.indent_level = 0
        self.debuginfo: dict[str, list[str]] = {"jac_mods": []}
        self.preamble = ast.EmptyToken()
        self.preamble.meta["py_code"] = "from __future__ import annotations\n"
        self.cur_arch = None  # tracks current architype during transpilation

    def enter_node(self, node: ast.AstNode) -> None:
        """Enter node."""
        if node:
            node.meta["py_code"] = ""
        return Pass.enter_node(self, node)

    def indent_str(self) -> str:
        """Return string for indent."""
        return " " * self.indent_size * self.indent_level

    def emit_ln(self, node: ast.AstNode, s: str) -> None:
        """Emit code to node."""
        self.emit(node, s.strip().strip("\n"))
        if node.meta["py_code"] and (
            len(spl := node.meta["py_code"].split()) < 3 or spl[-3] != "#"
        ):
            self.emit(node, f"  # {self.get_mod_index(node)} {node.loc.first_line}")
        self.emit(node, "\n")

    def emit_ln_unique(self, node: ast.AstNode, s: str) -> None:
        """Emit code to node."""
        if s not in node.meta["py_code"]:
            ilev = self.indent_level
            self.indent_level = 0
            self.emit_ln(node, s)
            self.indent_level = ilev

    def get_mod_index(self, node: ast.AstNode) -> int:
        """Get module index."""
        path = node.loc.mod_path
        if not path:
            return -1
        if path not in self.debuginfo["jac_mods"]:
            self.debuginfo["jac_mods"].append(path)
        return self.debuginfo["jac_mods"].index(path)

    def emit(self, node: ast.AstNode, s: str) -> None:
        """Emit code to node."""
        node.meta["py_code"] += self.indent_str() + s.replace(
            "\n", "\n" + self.indent_str()
        )
        if "\n" in node.meta["py_code"]:
            node.meta["py_code"] = node.meta["py_code"].rstrip(" ")

    def comma_sep_node_list(self, node: ast.SubNodeList) -> str:
        """Render comma separated node list."""
        node.meta["py_code"] = ", ".join([i.meta["py_code"] for i in node.items])
        return node.meta["py_code"]

    def dot_sep_node_list(self, node: ast.SubNodeList) -> str:
        """Render dot separated node list."""
        node.meta["py_code"] = ".".join([i.meta["py_code"] for i in node.items])
        return node.meta["py_code"]

    def nl_sep_node_list(self, node: ast.SubNodeList) -> str:
        """Render newline separated node list."""
        node.meta["py_code"] = ""
        for i in node.items:
            node.meta[
                "py_code"
            ] += f"{i.meta['py_code']}  # {self.get_mod_index(i)} {i.loc.first_line}\n"
        return node.meta["py_code"]

    def sep_node_list(self, node: ast.SubNodeList, delim: str = " ") -> str:
        """Render newline separated node list."""
        node.meta["py_code"] = f"{delim}".join([i.meta["py_code"] for i in node.items])
        return node.meta["py_code"]

    def needs_jac_import(self) -> None:
        """Check if import is needed."""
        self.emit_ln_unique(
            self.preamble, "from jaclang import jac_blue_import as __jac_import__"
        )

    def needs_enum(self) -> None:
        """Check if enum is needed."""
        self.emit_ln_unique(
            self.preamble,
            "from enum import Enum as __jac_Enum__, auto as __jac_auto__",
        )

    def emit_jac_error_handler(self, node: ast.AstNode) -> None:
        """Emit error handler."""
        self.emit_ln_unique(self.preamble, "import traceback as __jac_traceback__")
        self.emit_ln_unique(
            self.preamble, "from jaclang import handle_jac_error as __jac_error__"
        )
        self.emit_ln(node, "except Exception as e:")
        self.indent_level += 1
        # self.emit_ln(node, "__jac_traceback__.print_exc()")
        self.emit_ln(node, "tb = __jac_traceback__.extract_tb(e.__traceback__)")
        self.emit_ln(node, "__jac_tmp__ = __jac_error__(_jac_pycodestring_, e, tb)")
        # self.emit_ln(node, "print(__jac_tmp__)\nraise e")
        self.emit_ln(
            node,
            "e.args = (f'{e.args[0]}\\n' + __jac_tmp__,) + e.args[1:] "
            f"if '{Con.JAC_ERROR_PREAMBLE}' not in str(e) else e.args",
        )
        self.emit_ln(node, "raise e")
        self.indent_level -= 1

    def decl_def_missing(self, decl: str = "this") -> None:
        """Warn about declaration."""
        self.error(
            f"Unable to find definition for {decl} declaration. Perhaps there's an `include` missing?"
        )

    def ds_feature_warn(self) -> None:
        """Warn about feature."""
        self.warning("Data spatial features not supported in bootstrap Jac.")

    def exit_module(self, node: ast.Module) -> None:
        """Sub objects.

        name: str,
        doc: Optional[Constant],
        body: list[ElementStmt],
        mod_path: str,
        is_imported: bool,
        """
        if node.doc:
            self.emit_ln(node, node.doc.meta["py_code"])
        self.emit(node, self.preamble.meta["py_code"])
        if node.body:
            for i in node.body:
                self.emit(node, i.meta["py_code"])
        self.emit(node, f'r""" {Con.JAC_DEBUG_SPLITTER}\n')
        for i in self.debuginfo["jac_mods"]:
            self.emit(node, f"{i}\n")
        self.emit(node, f'{Con.JAC_DEBUG_SPLITTER} """\n')
        self.ir = node
        self.ir.meta["py_code"] = self.ir.meta["py_code"].rstrip()

    def exit_global_vars(self, node: ast.GlobalVars) -> None:
        """Sub objects.

        access: Optional[SubTag[Token]],
        assignments: SubNodeList[Assignment],
        is_frozen: bool,
        doc: Optional[String] = None,
        """
        if node.doc:
            self.emit_ln(node, node.doc.meta["py_code"])
        self.nl_sep_node_list(node.assignments)
        self.emit_ln(node, node.assignments.meta["py_code"])

    def exit_sub_tag(self, node: ast.SubTag) -> None:
        """Sub objects.

        tag: T,
        """
        self.emit(node, node.tag.meta["py_code"])

    def exit_sub_node_list(self, node: ast.SubNodeList) -> None:
        """Sub objects.

        items: list[T],
        """
        for i in node.items:
            self.emit(node, i.meta["py_code"])

    def exit_test(self, node: ast.Test) -> None:
        """Sub objects.

        name: Name | Token,
        body: SubNodeList[CodeBlockStmt],
        doc: Optional[Constant] = None,
        """
        test_name = node.name.meta["py_code"]
        test_code = "import unittest as __jac_unittest__\n"
        test_code += "__jac_tc__ = __jac_unittest__.TestCase()\n"
        test_code += "__jac_suite__ = __jac_unittest__.TestSuite()\n"
        test_code += "class __jac_check:\n"
        test_code += "    def __getattr__(self, name):\n"
        test_code += "        return getattr(__jac_tc__, 'assert'+name)"
        self.emit_ln_unique(self.preamble, test_code)
        self.emit_ln(node, f"def test_{test_name}():")
        self.indent_level += 1
        if node.doc:
            self.emit_ln(node, node.doc.meta["py_code"])
        self.emit_ln(node, "check = __jac_check()")
        if len(node.body.items):
            self.nl_sep_node_list(node.body)
            self.emit_ln(node, node.body.meta["py_code"])
        else:
            self.emit_ln(node, "pass")
        self.indent_level -= 1
        self.emit_ln(
            node,
            f"__jac_suite__.addTest(__jac_unittest__.FunctionTestCase(test_{test_name}))",
        )

    def exit_module_code(self, node: ast.ModuleCode) -> None:
        """Sub objects.

        name: Optional[SubTag[Name]],
        body: SubNodeList[CodeBlockStmt],
        doc: Optional[Constant] = None,
        """
        if node.doc:
            self.emit_ln(node, node.doc.meta["py_code"])
        if node.name:
            self.emit_ln(node, f"if __name__ == '{node.name.meta['py_code']}':")
            self.indent_level += 1
            self.nl_sep_node_list(node.body)
            self.emit_ln(node, node.body.meta["py_code"])
            self.indent_level -= 1
        else:
            self.nl_sep_node_list(node.body)
            self.emit_ln(node, node.body.meta["py_code"])

    def exit_py_inline_code(self, node: ast.PyInlineCode) -> None:
        """Sub objects.

        code: Token,
        doc: Optional[Constant] = None,
        """
        self.emit_ln(node, node.code.meta["py_code"])

    def exit_import(self, node: ast.Import) -> None:
        """Sub objects.

        lang: SubTag[Name],
        path: ModulePath,
        alias: Optional[Name],
        items: Optional[SubNodeList[ModuleItem]],
        is_absorb: bool,  # For includes
        doc: Optional[Constant] = None,
        sub_module: Optional[Module] = None,
        """
        if node.lang.tag.value == Con.JAC_LANG_IMP:  # injects module into sys.modules
            self.needs_jac_import()
            self.emit_ln(
                node,
                f"__jac_import__(target='{node.path.meta['py_code']}', base_path=__file__)",
            )
        if node.is_absorb:
            self.emit_ln(
                node,
                f"from {node.path.meta['py_code']} import *",
            )
            if node.items:
                self.warning(
                    "Includes import * in target module into current namespace."
                )
            return
        if not node.items:
            if not node.alias:
                self.emit_ln(node, f"import {node.path.meta['py_code']}")
            else:
                self.emit_ln(
                    node,
                    f"import {node.path.meta['py_code']} as {node.alias.meta['py_code']}",
                )
        else:
            self.comma_sep_node_list(node.items)
            self.emit_ln(
                node,
                f"from {node.path.meta['py_code']} import {node.items.meta['py_code']}",
            )

    def exit_module_path(self, node: ast.ModulePath) -> None:
        """Sub objects.

        path: list[Token],
        """
        self.emit(node, "".join([i.meta["py_code"] for i in node.path]))

    def exit_module_item(self, node: ast.ModuleItem) -> None:
        """Sub objects.

        name: Token,
        alias: Optional[Token],
        """
        if node.alias:
            self.emit(
                node, node.name.meta["py_code"] + " as " + node.alias.meta["py_code"]
            )
        else:
            self.emit(node, node.name.meta["py_code"])

    # NOTE: Incomplete for Jac Purple and Red
    def exit_architype(self, node: ast.Architype) -> None:
        """Sub objects.

        name: Name,
        arch_type: Token,
        access: Optional[SubTag[Token]],
        base_classes: Optional[SubNodeList[AtomType]],
        body: Optional[SubNodeList[ArchBlockStmt] | ArchDef],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
        """
        if node.decorators:
            for dec in node.decorators.items:  # renamed 'd' to 'dec'
                self.emit_ln(node, "@" + dec.meta["py_code"])
        if not node.base_classes:
            self.emit_ln(node, f"class {node.name.meta['py_code']}:")
        else:
            self.comma_sep_node_list(node.base_classes)
            self.emit_ln(
                node,
                f"class {node.name.meta['py_code']}({node.base_classes.meta['py_code']}):",
            )
        self.indent_level += 1
        if node.doc:
            self.emit_ln(node, node.doc.meta["py_code"])
        body = node.body.body if isinstance(node.body, ast.ArchDef) else node.body
        if body:
            init_func = None
            for itm in body.items:  # renamed 'b' to 'itm'
                if isinstance(itm, ast.Ability) and itm.py_resolve_name() == "__init__":
                    init_func = itm
                    break
            static_members = [
                i for i in body.items if isinstance(i, ast.ArchHas) and i.is_static
            ]
            for mem in static_members:  # renamed 'd' to 'mem'
                self.emit(node, mem.meta["py_code"])
                self.emit(node, "\n")

            if init_func and init_func.decorators:
                for dec in init_func.decorators.items:  # renamed 'd' to 'dec'
                    self.emit_ln(node, "@" + dec.meta["py_code"])
            self.emit_ln(node, "def __init__(self,")
            self.indent_level += 1
            if has_members := [
                i for i in body.items if isinstance(i, ast.ArchHas) and not i.is_static
            ]:
                for mem in has_members:  # renamed 'd' to 'mem'
                    for var in mem.vars.items:  # renamed 'j' to 'var'
                        self.emit_ln(node, f"{var.name.meta['py_code']} = None,")
            if init_func and init_func.signature:
                if "->" in init_func.signature.meta["py_code"]:
                    init_func.signature.meta["py_code"] = init_func.signature.meta[
                        "py_code"
                    ].split("->")[0]
                if len(init_func.signature.meta["py_code"]):
                    self.emit_ln(node, f"{init_func.signature.meta['py_code']},")
            self.emit_ln(node, " *args, **kwargs):")
            if not init_func:
                self.emit_ln(node, "super().__init__(*args, **kwargs)")
            for mem in has_members:  # renamed 'd' to 'mem'
                for var in mem.vars.items:  # renamed 'j' to 'var'
                    if var.value:
                        self.emit_ln(
                            node,
                            f"self.{var.name.meta['py_code']} = {var.value.meta['py_code']} "
                            f"if {var.name.meta['py_code']} is "
                            f"None else {var.name.meta['py_code']}",
                        )
                    else:
                        self.emit_ln(
                            node,
                            f"self.{var.name.meta['py_code']} = {var.name.meta['py_code']}",
                        )
            if init_func and init_func.body:
                ibody = (
                    init_func.body.body
                    if isinstance(init_func.body, ast.AbilityDef)
                    else init_func.body
                )
                self.nl_sep_node_list(ibody)
                self.emit_ln(node, f"{ibody.meta['py_code']}")
            self.indent_level -= 1
            for itm in body.items:  # renamed 'd' to 'itm'
                if itm not in has_members + static_members:
                    self.emit(node, itm.meta["py_code"])
                    self.emit(node, "\n")
        self.indent_level -= 1

    def exit_arch_def(self, node: ast.ArchDef) -> None:
        """Sub objects.

        target: ArchRefChain,
        body: SubNodeList[ArchBlockStmt],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
        """

    def exit_enum(self, node: ast.Enum) -> None:
        """Sub objects.

        name: Name,
        access: Optional[SubTag[Token]],
        base_classes: Optional[Optional[SubNodeList[AtomType]]],
        body: Optional[SubNodeList[EnumBlockStmt] | EnumDef],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
        """
        if node.decorators:
            for dec in node.decorators.items:  # Renamed 'i' to 'dec'
                self.emit_ln(node, "@" + dec.meta["py_code"])
        if not node.base_classes:
            self.needs_enum()
            self.emit_ln(node, f"class {node.name.meta['py_code']}(__jac_Enum__):")
        else:
            self.needs_enum()
            self.comma_sep_node_list(node.base_classes)
            self.emit_ln(
                node,
                f"class {node.name.meta['py_code']}({node.base_classes.meta['py_code']}, __jac_Enum__):",
            )
        self.indent_level += 1
        if node.doc:
            self.emit_ln(node, node.doc.meta["py_code"])
        body = node.body.body if isinstance(node.body, ast.EnumDef) else node.body
        if body:
            for itm in body.items:  # Renamed 'i' to 'itm'
                if isinstance(itm, ast.Name):
                    self.emit_ln(node, itm.meta["py_code"] + " = __jac_auto__()")
                else:
                    self.emit_ln(node, itm.meta["py_code"])
        self.indent_level -= 1

    def exit_enum_def(self, node: ast.EnumDef) -> None:
        """Sub objects.

        doc: Optional[Token],
        mod: Optional[DottedNameList],
        body: EnumBlock,
        """

    # NOTE: Incomplete for Jac Purple and Red
    def exit_ability(self, node: ast.Ability) -> None:
        """Sub objects.

        name_ref: NameType,
        is_func: bool,
        is_async: bool,
        is_static: bool,
        is_abstract: bool,
        is_method: bool,
        access: Optional[SubTag[Token]],
        signature: Optional[FuncSignature | SubNodeList[TypeSpec] | EventSignature],
        body: Optional[SubNodeList[CodeBlockStmt]],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
        """
        ability_name = node.py_resolve_name()
        if node.is_method and ability_name == "__init__":
            return
        if node.decorators:
            for dec in node.decorators.items:  # Renamed 'i' to 'dec'
                self.emit_ln(node, "@" + dec.meta["py_code"])
        if isinstance(node.signature, (ast.FuncSignature, ast.EventSignature)):
            if "->" in node.signature.meta["py_code"]:
                node.signature.meta["py_code"] = node.signature.meta["py_code"].replace(
                    " ->", ") ->"
                )
            else:
                node.signature.meta["py_code"] += ")"
            if node.is_method and not node.is_static:
                self.emit_ln(
                    node, f"def {ability_name}(self,{node.signature.meta['py_code']}:"
                )
            else:
                if node.is_method and node.is_static:
                    self.emit_ln(node, "@classmethod")
                self.emit_ln(
                    node, f"def {ability_name}({node.signature.meta['py_code']}:"
                )
        else:
            if node.is_method:
                self.emit_ln(node, f"def {ability_name}(self):")
            else:
                self.emit_ln(node, f"def {ability_name}():")
        self.indent_level += 1
        if node.doc:
            self.emit_ln(node, node.doc.meta["py_code"])
        body = node.body.body if isinstance(node.body, ast.AbilityDef) else node.body
        if body and len(body.items):
            self.emit_ln(node, "try:")
            self.indent_level += 1
            self.nl_sep_node_list(body)
            self.emit_ln(node, body.meta["py_code"])
            self.indent_level -= 1
            self.emit_jac_error_handler(node)
        elif node.is_abstract or (body and not len(body.items)):
            self.emit_ln(node, "pass")
        else:
            self.warning(f"No implementation for ability {ability_name}")
        self.indent_level -= 1

        # if len(node.stmts) == 0:
        #     self.emit_ln(node, "pass")
        # for i in node.stmts:
        #     self.emit(node, i.meta["py_code"])
        #     if len(i.meta["py_code"]) and i.meta["py_code"][-1] != "\n":
        #         self.emit_ln(node, "\n")

    def exit_ability_def(self, node: ast.AbilityDef) -> None:
        """Sub objects.

        target: ArchRefChain,
        signature: FuncSignature | EventSignature,
        body: SubNodeList[CodeBlockStmt],
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        decorators: Optional[SubNodeList[ExprType]] = None,
        """

    def exit_func_signature(self, node: ast.FuncSignature) -> None:
        """Sub objects.

        params: Optional[SubNodeList[ParamVar]],
        return_type: Optional[SubTag[ExprType]],
        """
        if node.params:
            self.comma_sep_node_list(node.params)
            self.emit(node, node.params.meta["py_code"])
        if node.return_type:
            self.emit(node, f" -> {node.return_type.tag.meta['py_code']}")

    # NOTE: Incomplete for Jac Purple and Red
    def exit_event_signature(self, node: ast.EventSignature) -> None:
        """Sub objects.

        event: Token,
        arch_tag_info: Optional[SubNodeList[TypeSpec]],
        return_type: Optional[SubTag[SubNodeList[TypeSpec]]],
        """
        self.error("Event style abilities not supported in bootstrap Jac")

    def exit_arch_ref_chain(self, node: ast.ArchRefChain) -> None:
        """Sub objects.

        archs: list[ArchRef],
        """
        self.emit(node, ".".join([i.meta["py_code"] for i in node.archs]))

    def exit_param_var(self, node: ast.ParamVar) -> None:
        """Sub objects.

        name: Name,
        unpack: Optional[Token],
        type_tag: SubTag[ExprType],
        value: Optional[ExprType],
        """
        if node.type_tag is None:
            raise self.ice()
        node.type_tag.meta["py_code"] = node.type_tag.tag.meta["py_code"]
        if node.unpack:
            self.emit(node, f"{node.unpack.meta['py_code']}")
        if node.value:
            self.emit(
                node,
                f"{node.name.meta['py_code']}: {node.type_tag.meta['py_code']} = {node.value.meta['py_code']}",
            )
        else:
            self.emit(
                node, f"{node.name.meta['py_code']}: {node.type_tag.meta['py_code']}"
            )

    def exit_arch_has(self, node: ast.ArchHas) -> None:
        """Sub objects.

        is_static: bool,
        access: Optional[SubTag[Token]],
        vars: SubNodeList[HasVar],
        is_frozen: bool,
        kid: list[AstNode],
        doc: Optional[Constant] = None,
        """
        self.nl_sep_node_list(node.vars)
        self.emit(node, node.vars.meta["py_code"])

    def exit_has_var(self, node: ast.HasVar) -> None:
        """Sub objects.

        name: Name,
        type_tag: SubTag[SubNodeList[TypeSpec]],
        value: Optional[ExprType],
        """
        if node.type_tag is None:
            raise self.ice()
        node.type_tag.meta["py_code"] = node.type_tag.tag.meta["py_code"]
        if node.value:
            self.emit(
                node,
                f"{node.name.meta['py_code']}: {node.type_tag.meta['py_code']} = {node.value.meta['py_code']}",
            )
        else:
            self.emit(
                node,
                f"{node.name.meta['py_code']}: {node.type_tag.meta['py_code']} = None",
            )

    def exit_typed_ctx_block(self, node: ast.TypedCtxBlock) -> None:
        """Sub objects.

        type_ctx: SubNodeList[TypeSpec],
        body: SubNodeList[CodeBlockStmt],
        """
        self.ds_feature_warn()

    def exit_if_stmt(self, node: ast.IfStmt) -> None:
        """Sub objects.

        condition: ExprType,
        body: SubNodeList[CodeBlockStmt],
        else_body: Optional[ElseStmt | ElseIf],
        """
        self.emit_ln(node, f"if {node.condition.meta['py_code']}:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1
        self.emit(node, "\n")
        if node.else_body:
            self.emit(node, node.else_body.meta["py_code"])

    def exit_else_if(self, node: ast.ElseIf) -> None:
        """Sub objects.

        condition: ExprType,
        body: SubNodeList[CodeBlockStmt],
        else_body: Optional[ElseStmt | ElseIf],
        """
        self.emit_ln(node, f"elif {node.condition.meta['py_code']}:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1
        if node.else_body:
            self.emit(node, node.else_body.meta["py_code"])

    def exit_else_stmt(self, node: ast.ElseStmt) -> None:
        """Sub objects.

        body: SubNodeList[CodeBlockStmt],
        """
        self.emit_ln(node, "else:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1
        self.emit(node, "\n")

    def exit_try_stmt(self, node: ast.TryStmt) -> None:
        """Sub objects.

        body: SubNodeList[CodeBlockStmt],
        excepts: Optional[SubNodeList[Except]],
        finally_body: Optional[FinallyStmt],
        """
        self.emit_ln(node, "try:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1
        if node.excepts:
            self.emit_ln(node, node.excepts.meta["py_code"])
        if node.finally_body:
            self.emit_ln(node, node.finally_body.meta["py_code"])

    def exit_except(self, node: ast.Except) -> None:
        """Sub objects.

        ex_type: ExprType,
        name: Optional[Token],
        body: SubNodeList[CodeBlockStmt],
        """
        if node.name:
            self.emit_ln(
                node,
                f"except {node.ex_type.meta['py_code']} as {node.name.meta['py_code']}:",
            )
        else:
            self.emit_ln(node, f"except {node.ex_type.meta['py_code']}:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1

    def exit_finally_stmt(self, node: ast.FinallyStmt) -> None:
        """Sub objects.

        body: SubNodeList[CodeBlockStmt],
        """
        self.emit_ln(node, "finally:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1

    def exit_iter_for_stmt(self, node: ast.IterForStmt) -> None:
        """Sub objects.

        iter: Assignment,
        condition: ExprType,
        count_by: ExprType,
        body: SubNodeList[CodeBlockStmt],
        """
        self.emit_ln(node, f"{node.iter.meta['py_code']}")
        self.emit_ln(node, f"while {node.condition.meta['py_code']}:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.emit_ln(node, f"{node.count_by.meta['py_code']}")
        self.indent_level -= 1

    def exit_in_for_stmt(self, node: ast.InForStmt) -> None:
        """Sub objects.

        name_list: SubNodeList[Name],
        collection: ExprType,
        body: SubNodeList[CodeBlockStmt],
        """
        self.comma_sep_node_list(node.name_list)
        names = node.name_list.meta["py_code"]
        self.emit_ln(node, f"for {names} in {node.collection.meta['py_code']}:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1
        # self.emit(node, ",".join([i.meta["py_code"] for i in node.names]))

    def exit_while_stmt(self, node: ast.WhileStmt) -> None:
        """Sub objects.

        condition: ExprType,
        body: SubNodeList[CodeBlockStmt],
        """
        self.emit_ln(node, f"while {node.condition.meta['py_code']}:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1

    def exit_with_stmt(self, node: ast.WithStmt) -> None:
        """Sub objects.

        exprs: SubNodeList[ExprAsItem],
        body: SubNodeList[CodeBlockStmt],
        """
        self.comma_sep_node_list(node.exprs)
        self.emit_ln(node, f"with {node.exprs.meta['py_code']}:")
        self.indent_level += 1

        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1
        # self.emit(node, ", ".join([i.meta["py_code"] for i in node.items]))

    def exit_expr_as_item(self, node: ast.ExprAsItem) -> None:
        """Sub objects.

        expr: ExprType,
        alias: Optional[Name],
        """
        if node.alias:
            self.emit(
                node, node.expr.meta["py_code"] + " as " + node.alias.meta["py_code"]
            )
        else:
            self.emit(node, node.expr.meta["py_code"])

    def exit_raise_stmt(self, node: ast.RaiseStmt) -> None:
        """Sub objects.

        cause: Optional[ExprType],
        """
        if node.cause:
            self.emit_ln(node, f"raise {node.cause.meta['py_code']}")
        else:
            self.emit_ln(node, "raise")

    def exit_assert_stmt(self, node: ast.AssertStmt) -> None:
        """Sub objects.

        condition: ExprType,
        error_msg: Optional[ExprType],
        """
        if node.error_msg:
            self.emit_ln(
                node,
                f"assert {node.condition.meta['py_code']}, {node.error_msg.meta['py_code']}",
            )
        else:
            self.emit_ln(node, f"assert {node.condition.meta['py_code']}")

    # NOTE: Incomplete for Jac Purple and Red
    def exit_ctrl_stmt(self, node: ast.CtrlStmt) -> None:
        """Sub objects.

        ctrl: Token,
        """
        if node.ctrl.name == Tok.KW_SKIP:
            self.ds_feature_warn()
        else:
            self.emit_ln(node, node.ctrl.meta["py_code"])

    def exit_delete_stmt(self, node: ast.DeleteStmt) -> None:
        """Sub objects.

        target: ExprType,
        """
        self.emit_ln(node, f"del {node.target.meta['py_code']}")

    # NOTE: Incomplete for Jac Purple and Red
    def exit_report_stmt(self, node: ast.ReportStmt) -> None:
        """Sub objects.

        expr: ExprType,
        """
        self.ds_feature_warn()

    def exit_return_stmt(self, node: ast.ReturnStmt) -> None:
        """Sub objects.

        expr: Optional[ExprType],
        """
        if node.expr:
            self.emit_ln(node, f"return {node.expr.meta['py_code']}")
        else:
            self.emit_ln(node, "return")

    def exit_yield_stmt(self, node: ast.YieldStmt) -> None:
        """Sub objects.

        expr: Optional[ExprType],
        """
        if node.expr:
            self.emit_ln(node, f"yield {node.expr.meta['py_code']}")
        else:
            self.emit_ln(node, "yield")

    # NOTE: Incomplete for Jac Purple and Red
    def exit_ignore_stmt(self, node: ast.IgnoreStmt) -> None:
        """Sub objects.

        target: ExprType,
        """
        self.ds_feature_warn()

    # NOTE: Incomplete for Jac Purple and Red
    def exit_visit_stmt(self, node: ast.VisitStmt) -> None:
        """Sub objects.

        vis_type: Optional[SubTag[SubNodeList[Name]]],
        target: ExprType,
        else_body: Optional[ElseStmt],
        from_walker: bool = False,
        """
        self.ds_feature_warn()

    # NOTE: Incomplete for Jac Purple and Red
    def exit_revisit_stmt(self, node: ast.RevisitStmt) -> None:
        """Sub objects.

        hops: Optional[ExprType],
        else_body: Optional[ElseStmt],
        """
        self.ds_feature_warn()

    # NOTE: Incomplete for Jac Purple and Red
    def exit_disengage_stmt(self, node: ast.DisengageStmt) -> None:
        """Sub objects."""
        self.ds_feature_warn()

    # NOTE: Incomplete for Jac Purple and Red
    def exit_await_stmt(self, node: ast.AwaitStmt) -> None:
        """Sub objects.

        target: ExprType,
        """
        self.ds_feature_warn()

    def exit_global_stmt(self, node: ast.GlobalStmt) -> None:
        """Sub objects.

        target: SubNodeList[NameType],
        """
        self.nl_sep_node_list(node.target)
        self.emit_ln(node, f"{node.target.meta['py_code']}")

    def exit_non_local_stmt(self, node: ast.GlobalStmt) -> None:
        """Sub objects.

        target: SubNodeList[NameType],
        """
        self.nl_sep_node_list(node.target)
        self.emit_ln(node, f"{node.target.meta['py_code']}")

    def exit_assignment(self, node: ast.Assignment) -> None:
        """Sub objects.

        target: SubNodeList[AtomType],
        value: Optional[ExprType | YieldStmt],
        type_tag: Optional[SubTag[ExprType]],
        is_static: bool = False,
        mutable: bool = True,
        """
        self.sep_node_list(node.target, delim="=")
        self.emit(node, node.target.meta["py_code"])
        if node.type_tag:
            self.emit(node, f": {node.type_tag.tag.meta['py_code']}")
        if node.value:
            self.emit(node, f" = {node.value.meta['py_code']}")

    # NOTE: Incomplete for Jac Purple and Red
    def exit_binary_expr(self, node: ast.BinaryExpr) -> None:
        """Sub objects.

        left: ExprType,
        right: ExprType,
        op: Token | DisconnectOp | ConnectOp,
        """
        if isinstance(node.op, (ast.DisconnectOp, ast.ConnectOp)):
            self.ds_feature_warn()
        if isinstance(node.op, ast.Token):
            if node.op.value in [
                *["+", "-", "*", "/", "%", "**"],
                *["+=", "-=", "*=", "/=", "%=", "**="],
                *[">>", "<<", ">>=", "<<="],
                *["//=", "&=", "|=", "^=", "~="],
                *["//", "&", "|", "^"],
                *[">", "<", ">=", "<=", "==", "!=", ":="],
                *["and", "or", "in", "not in", "is", "is not"],
            ]:
                self.emit(
                    node,
                    f"{node.left.meta['py_code']} {node.op.meta['py_code']} {node.right.meta['py_code']}",
                )
            elif node.op.name in [
                Tok.PIPE_FWD,
                Tok.KW_SPAWN,
                Tok.A_PIPE_FWD,
            ] and isinstance(node.left, ast.TupleVal):
                params = node.left.meta["py_code"]
                params = params.replace(",)", ")") if params[-2:] == ",)" else params
                self.emit(node, f"{node.right.meta['py_code']}{params}")
            elif node.op.name in [Tok.PIPE_BKWD, Tok.A_PIPE_BKWD] and isinstance(
                node.right, ast.TupleVal
            ):
                params = node.right.meta["py_code"]
                params = params.replace(",)", ")") if params[-2:] == ",)" else params
                self.emit(node, f"{node.left.meta['py_code']}{params}")
            elif node.op.name == Tok.PIPE_FWD and isinstance(node.right, ast.TupleVal):
                self.ds_feature_warn()
            elif node.op.name == Tok.PIPE_FWD:
                self.emit(
                    node, f"{node.right.meta['py_code']}({node.left.meta['py_code']}"
                )
                paren_count = (
                    node.meta["pipe_chain_count"]
                    if "pipe_chain_count" in node.meta
                    else 1
                )
                if (
                    isinstance(node.parent, ast.BinaryExpr)
                    and isinstance(node.parent.op, ast.Token)
                    and node.parent.op.name == Tok.PIPE_FWD
                ):
                    node.parent.meta["pipe_chain_count"] = paren_count + 1
                else:
                    self.emit(node, ")" * paren_count)

            elif node.op.name in [Tok.KW_SPAWN, Tok.A_PIPE_FWD]:
                self.emit(
                    node, f"{node.right.meta['py_code']}({node.left.meta['py_code']}"
                )
                paren_count = (
                    node.meta["a_pipe_chain_count"]
                    if "a_pipe_chain_count" in node.meta
                    else 1
                )
                if (
                    isinstance(node.parent, ast.BinaryExpr)
                    and isinstance(node.parent.op, ast.Token)
                    and node.parent.op.name
                    in [
                        Tok.KW_SPAWN,
                        Tok.A_PIPE_FWD,
                    ]
                ):
                    node.parent.meta["a_pipe_chain_count"] = paren_count + 1
                else:
                    self.emit(node, ")" * paren_count)

            elif node.op.name in [Tok.PIPE_BKWD, Tok.A_PIPE_BKWD]:
                self.emit(
                    node, f"{node.left.meta['py_code']}({node.right.meta['py_code']})"
                )
            elif node.op.name == Tok.ELVIS_OP:
                self.emit(
                    node,
                    f"{Con.JAC_TMP} "
                    f"if ({Con.JAC_TMP} := ({node.left.meta['py_code']})) is not None "
                    f"else {node.right.meta['py_code']}",
                )
            else:
                self.error(
                    f"Binary operator {node.op.value} not supported in bootstrap Jac"
                )

    def exit_lambda_expr(self, node: ast.LambdaExpr) -> None:
        """Sub objects.

        params: Optional[SubNodeList[ParamVar]],
        return_type: Optional[SubTag[ExprType]],
        body: ExprType,
        """
        out = ""
        if node.params:
            self.comma_sep_node_list(node.params)
            out += node.params.meta["py_code"]
        if node.return_type:
            out += f" -> {node.return_type.tag.meta['py_code']}"
        self.emit(node, f"lambda {out}: {node.body.meta['py_code']}")

    def exit_unary_expr(self, node: ast.UnaryExpr) -> None:
        """Sub objects.

        operand: ExprType,
        op: Token,
        """
        if node.op.value in ["-", "~", "+", "*", "**"]:
            self.emit(node, f"{node.op.meta['py_code']}{node.operand.meta['py_code']}")
        elif node.op.value == "not":
            self.emit(node, f"not {node.operand.meta['py_code']}")
        elif node.op.name in [Tok.PIPE_FWD, Tok.KW_SPAWN, Tok.A_PIPE_FWD]:
            self.emit(node, f"{node.operand.meta['py_code']}()")
        else:
            self.error(f"Unary operator {node.op.value} not supported in bootstrap Jac")

    def exit_if_else_expr(self, node: ast.IfElseExpr) -> None:
        """Sub objects.

        condition: ExprType,
        value: ExprType,
        else_value: ExprType,
        """
        self.emit(
            node,
            f"{node.value.meta['py_code']} if {node.condition.meta['py_code']} "
            f"else {node.else_value.meta['py_code']}",
        )

    def exit_multi_string(self, node: ast.MultiString) -> None:
        """Sub objects.

        strings: list[Token],
        """
        for string in node.strings:
            self.emit(node, string.meta["py_code"])

    def exit_f_string(self, node: ast.FString) -> None:
        """Sub objects.

        parts: Optional[SubNodeList[Constant | ExprType]],
        """
        self.emit(node, 'f"')
        if node.parts:
            for part in node.parts.items:
                if isinstance(part, ast.String) and part.name in [
                    Tok.FSTR_PIECE,
                    Tok.FSTR_BESC,
                ]:
                    self.emit(node, f"{part.meta['py_code']}")
                else:
                    self.emit(node, "{" + part.meta["py_code"] + "}")
        self.emit(node, '"')

    def exit_expr_list(self, node: ast.ExprList) -> None:
        """Sub objects.

        values: Optional[SubNodeList[ExprType]],
        """
        if node.values is not None:
            self.comma_sep_node_list(node.values)
            self.emit(
                node,
                f"{node.values.meta['py_code']}",
            )

    def exit_list_val(self, node: ast.ListVal) -> None:
        """Sub objects.

        values: Optional[SubNodeList[ExprType]],
        """
        if node.values is not None:
            self.comma_sep_node_list(node.values)
            self.emit(
                node,
                f"[{node.values.meta['py_code']}]",
            )
        else:
            self.emit(node, "[]")

    def exit_set_val(self, node: ast.SetVal) -> None:
        """Sub objects.

        values: Optional[SubNodeList[ExprType]],
        """
        if node.values is not None:
            self.comma_sep_node_list(node.values)
            self.emit(
                node,
                f"{{{node.values.meta['py_code']}}}",
            )

    def exit_tuple_val(self, node: ast.TupleVal) -> None:
        """Sub objects.

        values: Optional[SubNodeList[ExprType | Assignment]],
        """
        if node.values is not None:
            self.comma_sep_node_list(node.values)
            self.emit(
                node,
                f"({node.values.meta['py_code']})",
            )

    def exit_dict_val(self, node: ast.DictVal) -> None:
        """Sub objects.

        kv_pairs: list["KVPair"],
        """
        self.emit(
            node,
            f"{{{', '.join([kv_pair.meta['py_code'] for kv_pair in node.kv_pairs])}}}",
        )

    def exit_k_v_pair(self, node: ast.KVPair) -> None:
        """Sub objects.

        key: ExprType,
        value: ExprType,
        """
        self.emit(node, f"{node.key.meta['py_code']}: {node.value.meta['py_code']}")

    def exit_inner_compr(self, node: ast.InnerCompr) -> None:
        """Sub objects.

        out_expr: ExprType,
        names: SubNodeList[Name],
        collection: ExprType,
        conditional: Optional[ExprType],
        """
        self.comma_sep_node_list(node.names)
        names = node.names.meta["py_code"]
        partial = (
            f"{node.out_expr.meta['py_code']} for {names} "
            f"in {node.collection.meta['py_code']}"
        )
        if node.conditional:
            partial += f" if {node.conditional.meta['py_code']}"
        self.emit(node, f"({partial})")

    def exit_list_compr(self, node: ast.ListCompr) -> None:
        """Sub objects.

        compr: InnerCompr,
        """
        self.emit(node, f"[{node.compr.meta['py_code']}]")

    def exit_gen_compr(self, node: ast.GenCompr) -> None:
        """Sub objects.

        compr: InnerCompr,
        """
        self.emit(node, f"({node.compr.meta['py_code']},)")

    def exit_set_compr(self, node: ast.SetCompr) -> None:
        """Sub objects.

        compr: InnerCompr,
        """
        self.emit(node, f"{{{node.compr.meta['py_code']}}}")

    def exit_dict_compr(self, node: ast.DictCompr) -> None:
        """Sub objects.

        kv_pair: KVPair,
        names: SubNodeList[Name],
        collection: ExprType,
        conditional: Optional[ExprType],
        """
        names = node.names.meta["py_code"]
        partial = f"{node.kv_pair.meta['py_code']} for " f"{names}"
        partial += f" in {node.collection.meta['py_code']}"
        if node.conditional:
            partial += f" if {node.conditional.meta['py_code']}"
        self.emit(node, f"{{{partial}}}")

    def exit_atom_trailer(self, node: ast.AtomTrailer) -> None:
        """Sub objects.

        target: AtomType,
        right: AtomType,
        null_ok: bool,
        """
        if (
            isinstance(
                node.target, ast.AtomUnit
            )  # a bit complicated but works, checks if left is null_ok
            and node.target.is_null_ok
            or isinstance(node.target, ast.AtomTrailer)
            and isinstance(node.target.right, ast.AtomUnit)
            and node.target.right.is_null_ok
        ):
            if isinstance(node.right, (ast.IndexSlice, ast.ListVal)):
                self.emit(
                    node,
                    f"({node.target.meta['py_code']}{node.right.meta['py_code']} "
                    f"if {node.target.meta['py_code']} is not None else None)",
                )
            else:
                self.emit(
                    node,
                    f"({node.target.meta['py_code']}.{node.right.meta['py_code']} "
                    f"if {node.target.meta['py_code']} is not None else None)",
                )
        else:
            if isinstance(node.right, (ast.IndexSlice, ast.ListVal)):
                self.emit(
                    node,
                    f"{node.target.meta['py_code']}{node.right.meta['py_code']}",
                )
            else:
                self.emit(
                    node,
                    f"{node.target.meta['py_code']}.{node.right.meta['py_code']}",
                )

    def exit_atom_unit(self, node: ast.AtomUnit) -> None:
        """Sub objects.

        value: AtomType | ExprType,
        is_paren: bool,
        is_null_ok: bool,
        """
        if node.is_null_ok:
            self.emit(node, node.value.meta["py_code"])
        elif node.is_paren:
            self.emit(node, f"({node.value.meta['py_code']})")

    # NOTE: Incomplete for Jac Purple and Red
    def exit_func_call(self, node: ast.FuncCall) -> None:
        """Sub objects.

        target: AtomType,
        params: Optional[SubNodeList[ExprType | Assignment]],
        """
        if node.params:
            self.comma_sep_node_list(node.params)
            self.emit(
                node,
                f"{node.target.meta['py_code']}({node.params.meta['py_code']})",
            )
        else:
            self.emit(node, f"{node.target.meta['py_code']}()")

    def exit_index_slice(self, node: ast.IndexSlice) -> None:
        """Sub objects.

        start: Optional[ExprType],
        stop: Optional[ExprType],
        is_range: bool,
        """
        if node.is_range:
            self.emit(
                node,
                f"[{node.start.meta['py_code'] if node.start else ''}:"
                f"{node.stop.meta['py_code'] if node.stop else ''}]",
            )
        elif node.start:
            self.emit(node, f"[{node.start.meta['py_code']}]")
        else:
            self.ice("Something went horribly wrong.")

    # NOTE: Incomplete for Jac Purple and Red (maybe for global)
    def exit_arch_ref(self, node: ast.ArchRef) -> None:
        """Sub objects.

        name: Name,
        arch: Token,
        """
        self.emit(node, node.py_resolve_name())

    def exit_special_var_ref(self, node: ast.SpecialVarRef) -> None:
        """Sub objects.

        var: Token,
        """
        self.emit(node, node.py_resolve_name())

    # NOTE: Incomplete for Jac Purple and Red
    def exit_edge_op_ref(self, node: ast.EdgeOpRef) -> None:
        """Sub objects.

        filter_type: Optional[ExprType],
        filter_cond: Optional[SubNodeList[BinaryExpr]],
        edge_dir: EdgeDir,
        """
        self.ds_feature_warn()

    # NOTE: Incomplete for Jac Purple and Red
    def exit_disconnect_op(self, node: ast.DisconnectOp) -> None:
        """Sub objects.

        edge_spec: EdgeOpRef,
        """
        self.ds_feature_warn()

    # NOTE: Incomplete for Jac Purple and Red
    def exit_connect_op(self, node: ast.ConnectOp) -> None:
        """Sub objects.

        conn_type: Optional[ExprType],
        conn_assign: Optional[SubNodeList[Assignment]],
        edge_dir: EdgeDir,
        """
        self.ds_feature_warn()

    # NOTE: Incomplete for Jac Purple and Red (to consider)
    def exit_filter_compr(self, node: ast.FilterCompr) -> None:
        """Sub objects.

        compares: SubNodeList[BinaryExpr],
        """
        self.ds_feature_warn()

    def exit_token(self, node: ast.Token) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value)

    def exit_match_stmt(self, node: ast.MatchStmt) -> None:
        """Sub objects.

        target: SubNodeList[ExprType],
        cases: list[MatchCase],
        """
        self.comma_sep_node_list(node.target)
        self.emit_ln(node, f"match {node.target.meta['py_code']}:")
        self.indent_level += 1
        for case in node.cases:
            self.emit_ln(node, case.meta["py_code"])
        self.indent_level -= 1

    def exit_match_case(self, node: ast.MatchCase) -> None:
        """Sub objects.

        pattern: ExprType,
        guard: Optional[ExprType],
        body: SubNodeList[CodeBlockStmt],
        """
        if node.guard:
            self.emit_ln(
                node,
                f"case {node.pattern.meta['py_code']} if {node.guard.meta['py_code']}:",
            )
        else:
            self.emit(node, f"case {node.pattern.meta['py_code']}:")
        self.indent_level += 1
        self.nl_sep_node_list(node.body)
        self.emit_ln(node, node.body.meta["py_code"])
        self.indent_level -= 1

    def exit_match_or(self, node: ast.MatchOr) -> None:
        """Sub objects.

        list[MatchPattern],
        """
        self.emit(node, " | ".join([i.meta["py_code"] for i in node.patterns]))

    def exit_match_as(self, node: ast.MatchAs) -> None:
        """Sub objects.

        name: NameType,
        pattern: MatchPattern,
        """
        self.emit(
            node, f"{node.name.meta['py_code']} as {node.pattern.meta['py_code']}"
        )

    def exit_match_wild(self, node: ast.MatchWild) -> None:
        """Sub objects."""
        self.emit(node, "_")

    def exit_match_value(self, node: ast.MatchValue) -> None:
        """Sub objects.

        value: ExprType,
        """
        self.emit(node, node.value.meta["py_code"])

    def exit_match_singleton(self, node: ast.MatchSingleton) -> None:
        """Sub objects.

        value: Bool | Null,
        """
        self.emit(node, node.value.meta["py_code"])

    def exit_match_sequence(self, node: ast.MatchSequence) -> None:
        """Sub objects.

        values: list[MatchPattern],
        """
        self.emit(node, f"[{', '.join([i.meta['py_code'] for i in node.values])}]")

    def exit_match_mapping(self, node: ast.MatchMapping) -> None:
        """Sub objects.

        values: list[MatchKVPair | MatchStar],
        """
        self.emit(node, f"{{{', '.join([i.meta['py_code'] for i in node.values])}}}")

    def exit_match_k_v_pair(self, node: ast.MatchKVPair) -> None:
        """Sub objects.

        key: MatchPattern | NameType,
        value: MatchPattern,
        """
        self.emit(node, f"{node.key.meta['py_code']}: {node.value.meta['py_code']}")

    def exit_match_star(self, node: ast.MatchStar) -> None:
        """Sub objects.

        name: NameType,
        is_list: bool,
        """
        self.emit(node, f"{'*' if node.is_list else '**'}{node.name.meta['py_code']}")

    def exit_match_arch(self, node: ast.MatchArch) -> None:
        """Sub objects.

        name: NameType,
        arg_patterns: Optional[SubNodeList[MatchPattern]],
        kw_patterns: Optional[SubNodeList[MatchKVPair]],
        """
        self.emit(node, node.name.meta["py_code"])
        params = "("
        if node.arg_patterns:
            self.comma_sep_node_list(node.arg_patterns)
            params += node.arg_patterns.meta["py_code"]
        if node.kw_patterns:
            self.comma_sep_node_list(node.kw_patterns)
            params += node.kw_patterns.meta["py_code"]
        params += ")"
        self.emit(node, params)

    def exit_name(self, node: ast.Name) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value if node.name != Tok.KWESC_NAME else node.value[2:])

    def exit_float(self, node: ast.Float) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value)

    def exit_int(self, node: ast.Int) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value)

    def exit_string(self, node: ast.String) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value)

    def exit_bool(self, node: ast.Bool) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value)

    def exit_null(self, node: ast.Null) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value)

    def exit_builtin_type(self, node: ast.BuiltinType) -> None:
        """Sub objects.

        name: str,
        value: str,
        line: int,
        col_start: int,
        col_end: int,
        pos_start: int,
        pos_end: int,
        """
        self.emit(node, node.value)

    def exit_semi(self, node: ast.Semi) -> None:
        """Sub objects."""
