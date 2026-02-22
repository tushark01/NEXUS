"""Tests for WorkingMemory."""

import pytest

from nexus.llm.schemas import Message
from nexus.memory.working import WorkingMemory


class TestWorkingMemory:
    def test_add_and_get(self):
        wm = WorkingMemory()
        wm.add_message("s1", Message(role="user", content="hi"))
        msgs = wm.get_messages("s1")
        assert len(msgs) == 1
        assert msgs[0].content == "hi"

    def test_multiple_sessions(self):
        wm = WorkingMemory()
        wm.add_message("s1", Message(role="user", content="a"))
        wm.add_message("s2", Message(role="user", content="b"))
        assert len(wm.get_messages("s1")) == 1
        assert len(wm.get_messages("s2")) == 1
        assert wm.get_messages("s1")[0].content == "a"

    def test_clear_session(self):
        wm = WorkingMemory()
        wm.add_message("s1", Message(role="user", content="a"))
        wm.clear_session("s1")
        assert wm.get_messages("s1") == []

    def test_eviction_preserves_system(self):
        wm = WorkingMemory(max_messages=5)
        wm.add_message("s1", Message(role="system", content="sys"))
        for i in range(10):
            wm.add_message("s1", Message(role="user", content=f"msg{i}"))

        msgs = wm.get_messages("s1")
        assert len(msgs) <= 5
        # System message should still be there
        assert any(m.role == "system" for m in msgs)

    def test_has_session(self):
        wm = WorkingMemory()
        assert not wm.has_session("s1")
        wm.add_message("s1", Message(role="user", content="hi"))
        assert wm.has_session("s1")

    def test_active_sessions(self):
        wm = WorkingMemory()
        wm.add_message("s1", Message(role="user", content="a"))
        wm.add_message("s2", Message(role="user", content="b"))
        assert set(wm.active_sessions) == {"s1", "s2"}

    def test_empty_session(self):
        wm = WorkingMemory()
        assert wm.get_messages("nonexistent") == []
