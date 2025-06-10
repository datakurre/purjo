from robot.errors import DataError  # type: ignore
from robot.parsing.model.statements import Statement  # type: ignore
from robot.running import TestDefaults  # type: ignore
from robot.running import TestSuite
from robot.running.builder.parsers import RobotParser as BaseParser  # type: ignore
from robot.running.model import Body  # type: ignore
from robot.running.model import Var as BaseVar
from robot.variables import VariableScopes  # type: ignore
from typing import Any
import datetime
import json
import os
import pathlib


BPMN_TASK_SCOPE = "BPMN_TASK_SCOPE"
BPMN_PROCESS_SCOPE = "BPMN_PROCESS_SCOPE"


def json_serializer(obj: Any) -> str:
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, pathlib.Path):
        return f"{obj.absolute()}"
    raise TypeError(f"Type {type(obj)} not serializable")


def set_bpmn_task(self: VariableScopes, name: str, value: Any) -> None:
    assert BPMN_TASK_SCOPE in os.environ
    path = pathlib.Path(os.environ[BPMN_TASK_SCOPE])
    data = json.loads(path.read_text()) if path.exists() else {}
    data[name[2:-1]] = value
    path.write_text(json.dumps(data, default=json_serializer))


def set_bpmn_process(self: VariableScopes, name: str, value: Any) -> None:
    assert BPMN_PROCESS_SCOPE in os.environ
    path = pathlib.Path(os.environ[BPMN_PROCESS_SCOPE])
    data = json.loads(path.read_text()) if path.exists() else {}
    data[name[2:-1]] = value
    path.write_text(json.dumps(data, default=json_serializer))


VariableScopes.set_bpmn = set_bpmn_task
VariableScopes.set_bpmn_task = set_bpmn_task
VariableScopes.set_bpmn_process = set_bpmn_process

Statement.statement_handlers["VAR"].options["scope"] = tuple(
    list(Statement.statement_handlers["VAR"].options["scope"])
    + ["BPMN:PROCESS", "BPMN:TASK"]
)


@Body.register
class Var(BaseVar):  # type: ignore
    def _get_scope(self, variables: Any) -> Any:
        if not self.scope:
            return "local", {}
        try:
            scope = variables.replace_string(self.scope)
            if scope.upper() in ("BPMN:TASK", "BPMN:PROCESS"):
                return scope.lower().replace(":", "_"), {}
        except DataError as err:
            raise DataError(f"Invalid VAR scope: {err}")
        return super()._get_scope(variables)


class RobotParser(BaseParser):  # type: ignore
    extension = ".robot"

    def parse(self, source: pathlib.Path, defaults: TestDefaults) -> TestSuite:
        return super().parse_suite_file(source, defaults)

    def parse_init(self, source: pathlib.Path, defaults: TestDefaults) -> TestSuite:
        return super().parse_init_file(source, defaults)


class PythonParser(BaseParser):  # type: ignore
    """Opinionated parser to support wrapping of a single configured Python function as a Robot Framework test case.
    The function should be specified in the format `module.function`, where `module` is the name of the Python module.
    """

    extension = ".py"

    def __init__(self, fqfn: str = ""):
        self.fqfn = fqfn

    def parse(self, source: pathlib.Path, defaults: TestDefaults) -> TestSuite:
        # Sanity check for missing or invalid configuration
        if not self.fqfn or "." not in self.fqfn:
            return TestSuite()

        module_path, function_name = self.fqfn.rsplit(".", 1)
        # Check if the module_path matches the source
        if not source.name.startswith(module_path):
            return TestSuite()

        # Dynamically generate a TestSuite
        suite = TestSuite(name=self.fqfn.split(".")[0])

        # Import the module in module_path as a library
        suite.resource.imports.library(module_path)

        # Create a single test case
        test_case = suite.tests.create(name=self.fqfn)

        # Add a single keyword to the test case that calls the function in function_name
        test_case.body.create_keyword(name=function_name)

        return suite

    def parse_init(self, source: pathlib.Path, defaults: TestDefaults) -> TestSuite:
        return TestSuite()


__all__ = ["RobotParser", "PythonParser"]
