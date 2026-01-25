"""Process definition migration utilities."""

from operaton.tasks import operaton_session
from operaton.tasks import settings as operaton_settings
from operaton.tasks.types import MigrationExecutionDto
from operaton.tasks.types import MigrationPlanGenerationDto
from operaton.tasks.types import ProcessDefinitionDto
from operaton.tasks.types import ProcessInstanceDto
from typing import Any
from typing import Dict
from typing import List
import asyncio


async def migrate(target: ProcessDefinitionDto, verbose: bool) -> None:
    """Migrate all instances of a process definition to another definition."""
    assert target.id
    assert target.key
    async with operaton_session() as session:
        instances = [
            ProcessInstanceDto(**row)
            for row in await (
                await session.get(
                    f"{operaton_settings.ENGINE_REST_BASE_URL}/process-instance",
                    params={"processDefinitionKey": target.key},
                )
            ).json()
        ]
        ids_by_definitions: Dict[str, List[str]] = {}
        for instance in instances:
            if instance.id and instance.id != target.id and instance.definitionId:
                ids_by_definitions.setdefault(instance.definitionId, [])
                ids_by_definitions[instance.definitionId].append(instance.id)
        plans: Dict[str, Any] = {}
        for definition in ids_by_definitions:
            plans[definition] = await (
                await session.post(
                    f"{operaton_settings.ENGINE_REST_BASE_URL}/migration/generate",
                    json=MigrationPlanGenerationDto(
                        sourceProcessDefinitionId=definition,
                        targetProcessDefinitionId=target.id,
                        updateEventTriggers=True,
                    ).model_dump(),
                )
            ).json()
        results = (
            await asyncio.gather(
                *[
                    session.post(
                        f"{operaton_settings.ENGINE_REST_BASE_URL}/migration/execute",
                        json=MigrationExecutionDto(
                            migrationPlan=plans[definition],
                            processInstanceIds=instances,
                            skipCustomListeners=False,
                            skipIoMappings=True,
                        ).model_dump(),
                    )
                    for definition, instances in ids_by_definitions.items()
                ]
            )
            if ids_by_definitions
            else []
        )
        if verbose:
            print([await response.json() for response in results])
