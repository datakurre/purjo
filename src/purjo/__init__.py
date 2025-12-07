from purjo.Purjo import Purjo as purjo


try:
    from purjo.data.RobotParser import PythonParser
    from purjo.data.RobotParser import RobotParser

    __all__ = ["purjo", "PythonParser", "RobotParser"]
except ModuleNotFoundError:  # PythonParser depends on robot
    __all__ = ["purjo"]
