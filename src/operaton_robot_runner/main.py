from operaton.tasks import serve
import operaton_robot_runner.task


assert operaton_robot_runner.task  # register task


def main() -> None:
    serve()
