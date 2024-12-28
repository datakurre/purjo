from operaton.tasks.config import logger
from operaton_robot_runner.utils import lazydecode
from pathlib import Path
from typing import Dict
from typing import List
from typing import Tuple
import asyncio
import os
import re


async def run(
    program: str, args: List[str], cwd: str, env: Dict[str, str]
) -> Tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        program,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=os.environ | env | {"PYTHONPATH": ""},
    )

    stdout, stderr = await proc.communicate()
    stdout = stdout.strip() or b""
    stderr = stderr.strip() or b""

    if stderr:
        logger.debug("%s", lazydecode(stderr))
    if stdout:
        logger.debug("%s", lazydecode(stdout))

    logger.debug(f"exit code {proc.returncode}")

    return proc.returncode or 0, stdout, stderr


def fail_reason(robot_dir: str) -> str:
    reason = ""
    for file_path in Path(robot_dir).glob("*/**/output.xml"):
        xml = file_path.read_text()
        for match in re.findall(r'status="FAIL"[^>]*.([^<]*)', xml, re.M):
            match = match.strip()
            reason = match if match else reason
    return reason
