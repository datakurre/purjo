from purjo.Purjo import Purjo as purjo


try:
    from purjo.data.RobotParser import PythonParser  # noqa: F401
    from purjo.data.RobotParser import RobotParser  # noqa: F401

    __all__ = ["purjo", "PythonParser", "RobotParser"]
except ModuleNotFoundError:  # PythonParser depends on robot
    __all__ = ["purjo"]
