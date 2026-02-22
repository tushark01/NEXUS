"""Tests for Task and TaskDAG."""

import pytest

from nexus.agents.task import Task, TaskDAG, TaskStatus


class TestTask:
    def test_task_defaults(self):
        t = Task(title="Test", description="Do something")
        assert t.status == TaskStatus.PENDING
        assert t.parent_id is None
        assert t.depends_on == []
        assert t.assigned_to is None
        assert t.result is None
        assert t.id  # auto-generated

    def test_task_with_deps(self):
        t = Task(title="Test", description="Dep", depends_on=["t1", "t2"])
        assert t.depends_on == ["t1", "t2"]


class TestTaskDAG:
    def test_add_and_get(self):
        dag = TaskDAG()
        t = Task(id="t1", title="First", description="desc")
        dag.add_task(t)
        assert dag.get_task("t1") is t
        assert dag.get_task("nonexistent") is None

    def test_get_ready_no_deps(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.add_task(Task(id="t2", title="B", description="b"))
        ready = dag.get_ready_tasks()
        assert len(ready) == 2

    def test_get_ready_with_deps(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.add_task(Task(id="t2", title="B", description="b", depends_on=["t1"]))

        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "t1"

    def test_mark_completed_unblocks(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.add_task(Task(id="t2", title="B", description="b", depends_on=["t1"]))

        newly_ready = dag.mark_completed("t1", result="done")
        assert any(t.id == "t2" for t in newly_ready)

    def test_mark_failed(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.mark_failed("t1", "something broke")
        task = dag.get_task("t1")
        assert task.status == TaskStatus.FAILED
        assert task.error == "something broke"

    def test_is_complete(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.add_task(Task(id="t2", title="B", description="b"))

        assert not dag.is_complete
        dag.mark_completed("t1")
        assert not dag.is_complete
        dag.mark_completed("t2")
        assert dag.is_complete

    def test_is_complete_with_failed(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.mark_failed("t1", "err")
        assert dag.is_complete

    def test_get_results(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.add_task(Task(id="t2", title="B", description="b"))
        dag.mark_completed("t1", result="result_a")
        dag.mark_completed("t2", result="result_b")
        results = dag.get_results()
        assert results == {"t1": "result_a", "t2": "result_b"}

    def test_summary(self):
        dag = TaskDAG()
        dag.add_task(Task(id="t1", title="A", description="a"))
        dag.add_task(Task(id="t2", title="B", description="b", depends_on=["t1"]))
        s = dag.summary()
        assert "t1" in s
        assert "t2" in s

    def test_parallel_chains(self):
        """Two independent chains should both be ready at start."""
        dag = TaskDAG()
        dag.add_task(Task(id="a1", title="A1", description=""))
        dag.add_task(Task(id="a2", title="A2", description="", depends_on=["a1"]))
        dag.add_task(Task(id="b1", title="B1", description=""))
        dag.add_task(Task(id="b2", title="B2", description="", depends_on=["b1"]))

        ready = dag.get_ready_tasks()
        ids = {t.id for t in ready}
        assert ids == {"a1", "b1"}
