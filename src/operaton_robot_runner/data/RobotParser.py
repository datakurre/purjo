from robot.errors import DataError
from robot.running import TestDefaults
from robot.running import TestSuite
from robot.running.builder.parsers import RobotParser as BaseParser
from robot.running.model import Body
from robot.running.model import Var as BaseVar
from robot.variables import VariableScopes
import json
import os
import pathlib


BPMN_TASK_SCOPE = "BPMN_TASK_SCOPE"


def set_bpmn_task(self, name, value):
    assert BPMN_TASK_SCOPE in os.environ
    path = pathlib.Path(os.environ[BPMN_TASK_SCOPE])
    data = json.loads(path.read_text()) if path.exists() else {}
    data[name[2:-1]] = value
    path.write_text(json.dumps(data))


def set_bpmn_process(self, name, value):
    raise NotImplementedError()


VariableScopes.set_bpmn = set_bpmn_task
VariableScopes.set_bpmn_task = set_bpmn_task
VariableScopes.set_bpmn_process = set_bpmn_process


@Body.register
class Var(BaseVar):
    def _get_scope(self, variables):
        if not self.scope:
            return "local", {}
        try:
            scope = variables.replace_string(self.scope)
            if scope.upper() in ("BPMN", "BPMN:TASK", "BPMN:PROCESS"):
                return scope.lower().replace(":", "_"), {}
        except DataError as err:
            raise DataError(f"Invalid VAR scope: {err}")
        return super()._get_scope(variables)


class RobotParser(BaseParser):
    extension = ".robot"

    def parse(self, source: pathlib.Path, defaults: TestDefaults) -> TestSuite:
        return super().parse_suite_file(source, defaults)

    def parse_init(self, source: pathlib.Path, defaults: TestDefaults) -> TestSuite:
        return super().parse_init_file(source, defaults)


__all__ = ["RobotParser"]
