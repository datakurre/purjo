from pydantic_settings import BaseSettings
import enum


class OnFail(str, enum.Enum):
    FAIL = "FAIL"
    COMPLETE = "COMPLETE"


class Settings(BaseSettings):
    TASKS_TOPIC: str = "robotframework"
    TASKS_MAX_JOBS: int = 1
    BUSINESS_KEY: str = "businessKey"
    UV_EXECUTABLE: str = "uv"
    ROBOT_EXECUTABLE: str = "robot"


settings = Settings()


__all__ = ["settings"]
