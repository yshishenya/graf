from dataclasses import dataclass, field


@dataclass
class FakeTemporalClient:
    starts: dict[str, dict[str, object]] = field(default_factory=dict)

    async def start_workflow(
        self,
        workflow: object,
        payload: object,
        *,
        id: str,
        task_queue: str,
    ) -> dict[str, object]:
        if id in self.starts:
            return self.starts[id]
        handle = {"workflow_id": id, "run_id": f"run-{len(self.starts) + 1}", "payload": payload, "workflow": workflow, "task_queue": task_queue}
        self.starts[id] = handle
        return handle
