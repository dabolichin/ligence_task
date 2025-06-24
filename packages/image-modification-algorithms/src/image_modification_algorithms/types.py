from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from PIL import Image


@runtime_checkable
class SerializableOperation(Protocol):
    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "SerializableOperation": ...


@dataclass(frozen=True)
class PixelOperation(SerializableOperation):
    row: int
    col: int
    channel: int | None = None  # None for grayscale, 0-2 for RGB
    parameter: int = 0  # Operation parameter (e.g., XOR key)

    def to_tuple(self) -> tuple:
        if self.channel is None:
            return (self.row, self.col)
        return (self.row, self.col, self.channel)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "col": self.col,
            "channel": self.channel,
            "parameter": self.parameter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PixelOperation":
        return cls(
            row=data["row"],
            col=data["col"],
            channel=data.get("channel"),
            parameter=data.get("parameter", 0),
        )


@dataclass(frozen=True)
class Modification:
    algorithm_type: str
    image_mode: str
    operations: list[SerializableOperation]


@dataclass(frozen=True)
class ModificationResult:
    modified_image: Image.Image
    instructions: Modification


@runtime_checkable
class ModificationAlgorithm(Protocol):
    @abstractmethod
    def apply_modifications(
        self, image: Image.Image, num_modifications: int
    ) -> ModificationResult:
        """Apply modifications to an image and return result with instructions."""
        ...

    @staticmethod
    @abstractmethod
    def reverse_modifications(
        modified_image: Image.Image, instructions: Modification
    ) -> Image.Image:
        """Reverse modifications using the provided instructions."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Get the algorithm name identifier."""
        ...
