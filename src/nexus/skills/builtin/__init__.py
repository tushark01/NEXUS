"""Built-in NEXUS skills."""

from nexus.skills.builtin.code_exec import CodeExecSkill
from nexus.skills.builtin.file_ops import FileOpsSkill
from nexus.skills.builtin.notes import NotesSkill
from nexus.skills.builtin.shell import ShellSkill
from nexus.skills.builtin.web_search import WebSearchSkill

ALL_BUILTIN_SKILLS = [
    WebSearchSkill,
    FileOpsSkill,
    CodeExecSkill,
    NotesSkill,
    ShellSkill,
]
