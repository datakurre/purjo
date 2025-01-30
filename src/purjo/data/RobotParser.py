from robot.errors import DataError  # type: ignore
from robot.parsing.model.statements import Statement  # type: ignore
from robot.running import TestDefaults  # type: ignore
from robot.running import TestSuite
from robot.running.builder.parsers import RobotParser as BaseParser  # type: ignore
from robot.running.model import Body  # type: ignore
from robot.running.model import Var as BaseVar
from robot.variables import VariableScopes  # type: ignore
from typing import Any
import json
import os
import pathlib


BPMN_TASK_SCOPE = "BPMN_TASK_SCOPE"
BPMN_PROCESS_SCOPE = "BPMN_PROCESS_SCOPE"


def set_bpmn_task(self: VariableScopes, name: str, value: Any) -> None:
    assert BPMN_TASK_SCOPE in os.environ
    path = pathlib.Path(os.environ[BPMN_TASK_SCOPE])
    data = json.loads(path.read_text()) if path.exists() else {}
    data[name[2:-1]] = value
    path.write_text(json.dumps(data))


def set_bpmn_process(self: VariableScopes, name: str, value: Any) -> None:
    assert BPMN_PROCESS_SCOPE in os.environ
    path = pathlib.Path(os.environ[BPMN_PROCESS_SCOPE])
    data = json.loads(path.read_text()) if path.exists() else {}
    data[name[2:-1]] = value
    path.write_text(json.dumps(data))


VariableScopes.set_bpmn = set_bpmn_task
VariableScopes.set_bpmn_task = set_bpmn_task
VariableScopes.set_bpmn_process = set_bpmn_process

Statement.statement_handlers["VAR"].options["scope"] = tuple(
    list(Statement.statement_handlers["VAR"].options["scope"])
    + ["BPMN", "BPMN:TASK", "BPMN:PROCESS"]
)


@Body.register
class Var(BaseVar):  # type: ignore
    def _get_scope(self, variables: Any) -> Any:
        if not self.scope:
            return "local", {}
        try:
            scope = variables.replace_string(self.scope)
            if scope.upper() in ("BPMN", "BPMN:TASK", "BPMN:PROCESS"):
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


__all__ = ["RobotParser"]
