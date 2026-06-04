from dataclasses import dataclass, field


@dataclass
class FakeMinioStorage:
    objects: dict[str, bytes] = field(default_factory=dict)
    ensured: bool = False

    def ensure_bucket(self) -> None:
        self.ensured = True

    def put_bytes(self, object_key: str, data: bytes) -> None:
        self.objects[object_key] = data
