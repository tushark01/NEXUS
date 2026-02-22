"""Shared test fixtures for NEXUS."""

import pytest

from nexus.memory.working import WorkingMemory
from nexus.memory.manager import MemoryManager


@pytest.fixture
def working_memory():
    return WorkingMemory()


@pytest.fixture
def memory_manager(working_memory):
    return MemoryManager(working=working_memory)
