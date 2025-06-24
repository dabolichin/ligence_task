from unittest.mock import Mock

import pytest
from image_modification_algorithms.types import (
    ModificationAlgorithm,
    PixelOperation,
)

from src.verification_service.app.services.instruction_parser import InstructionParser


@pytest.fixture
def mock_xor_algorithm():
    mock_algorithm = Mock(spec=ModificationAlgorithm)
    mock_algorithm.get_name.return_value = "xor_transform"
    mock_algorithm.get_operation_class.return_value = PixelOperation
    return mock_algorithm


@pytest.fixture
def instruction_parser():
    return InstructionParser()


@pytest.fixture
def sample_pixel_operations_data():
    return [
        {"row": 10, "col": 20, "channel": 1, "parameter": 255},
        {"row": 5, "col": 8, "channel": 0, "parameter": 128},
        {"row": 15, "col": 25},  # Missing optional fields
    ]


@pytest.fixture
def sample_grayscale_operations_data():
    return [
        {"row": 3, "col": 7, "parameter": 100},
        {"row": 12, "col": 18, "parameter": 200},
    ]


@pytest.fixture
def sample_custom_operations_data():
    return [
        {"value": 42},
        {"value": 100},
    ]
