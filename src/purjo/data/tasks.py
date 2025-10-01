from pydantic import BaseModel
from robot.api import logger
from robot.libraries import BuiltIn
from typing import Literal
import json


VariableScope = Literal["BPMN:TASK", "BPMN:PROCESS"]


class InputVariables(BaseModel):
    name: str = "John Doe"


class OutputVariables(BaseModel):
    message: str


def get_variables() -> InputVariables:
    library = BuiltIn.BuiltIn()
    return InputVariables(**library.get_variables(no_decoration=True))


def set_variables(
    variables: OutputVariables, scope: VariableScope = "BPMN:PROCESS"
) -> None:
    library = BuiltIn.BuiltIn()
    try:
        if scope == "BPMN:TASK":
            for name, value in variables.model_dump().items():
                library._variables.set_bpmn_task(f"${{{name}}}", value)
        else:
            for name, value in variables.model_dump().items():
                library._variables.set_bpmn_process(f"${{{name}}}", value)
    except AssertionError:
        logger.info(json.dumps(variables.model_dump(), indent=2))


def main():
    variables = get_variables()
    set_variables(OutputVariables(message=f"Hello, {variables.name}!"))


if __name__ == "__main__":
    from purjo import PythonParser
    from robot import run

    run(__file__, parser=PythonParser("tasks.main"))
