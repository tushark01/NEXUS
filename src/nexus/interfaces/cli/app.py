"""NEXUS Rich CLI — beautiful terminal interface with streaming and swarm support."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nexus.llm.schemas import LLMRequest, Message

if TYPE_CHECKING:
    from nexus.agents.orchestrator import SwarmOrchestrator
    from nexus.llm.router import ModelRouter
    from nexus.memory.manager import MemoryManager
    from nexus.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

BANNER = r"""
    _   _  _____  __  __  _   _  ____
   | \ | || ____|\ \/ / | | | |/ ___|
   |  \| ||  _|   \  /  | | | |\___ \
   | |\  || |___  /  \  | |_| | ___) |
   |_| \_||_____|/_/\_\  \___/ |____/

   Network of Evolving eXpert Unified Systems
"""

SYSTEM_PROMPT = """You are NEXUS, a hyper-intelligent AI assistant framework. You are helpful, \
precise, and creative. You can reason about complex tasks, break them down, and provide \
thoughtful responses. When you don't know something, say so. Be concise but thorough."""


class NexusCLI:
    """Rich terminal interface for NEXUS with swarm and skill integration."""

    def __init__(
        self,
        router: ModelRouter,
        memory: MemoryManager,
        swarm: SwarmOrchestrator | None = None,
        skills: SkillRegistry | None = None,
    ) -> None:
        self._router = router
        self._memory = memory
        self._swarm = swarm
        self._skills = skills
        self._console = Console()
        self._session_id = "cli"
        self._swarm_mode = False

    async def run(self) -> None:
        """Main REPL loop."""
        self._console.print(Panel(BANNER, style="bold cyan", expand=False))

        status_parts = [f"Providers: {', '.join(self._router.available_providers)}"]
        if self._swarm:
            status_parts.append("Swarm: [green]active[/green]")
        if self._skills:
            status_parts.append(f"Skills: {len(self._skills.list_skills())}")
        status_parts.append("Type /help for commands | /quit to exit")

        self._console.print(f"[dim]{' | '.join(status_parts)}[/dim]\n")

        self._memory.add_message(
            self._session_id,
            Message(role="system", content=SYSTEM_PROMPT),
        )

        while True:
            try:
                prompt_style = "[bold magenta]Swarm >[/]" if self._swarm_mode else "[bold green]You >[/]"
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._console.input(prompt_style + " ")
                )
            except (EOFError, KeyboardInterrupt):
                self._console.print("\n[dim]Goodbye![/dim]")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                should_quit = await self._handle_command(user_input)
                if should_quit:
                    break
                continue

            if self._swarm_mode and self._swarm:
                await self._swarm_chat(user_input)
            else:
                await self._chat(user_input)

    async def _chat(self, user_input: str) -> None:
        """Send user message to LLM and stream the response."""
        self._memory.add_message(
            self._session_id,
            Message(role="user", content=user_input),
        )

        memory_context = await self._memory.get_context_for_prompt(user_input)
        messages = self._memory.get_messages(self._session_id)

        if memory_context:
            augmented_messages = list(messages)
            augmented_messages.insert(
                -1, Message(role="system", content=memory_context)
            )
        else:
            augmented_messages = messages

        request = LLMRequest(messages=augmented_messages, stream=True)

        full_response = ""
        self._console.print()

        try:
            with Live(Text("Thinking...", style="dim"), console=self._console, refresh_per_second=15) as live:
                async for chunk in self._router.stream(request):
                    if chunk.is_final:
                        break
                    full_response += chunk.content
                    try:
                        live.update(Markdown(full_response))
                    except Exception:
                        live.update(Text(full_response))

            self._memory.add_message(
                self._session_id,
                Message(role="assistant", content=full_response),
            )

            await self._memory.store_episodic(
                f"User: {user_input}\nAssistant: {full_response[:200]}",
                metadata={"session_id": self._session_id},
            )

        except Exception as e:
            self._console.print(f"\n[bold red]Error:[/] {e}")
            logger.exception("Chat error")

        self._console.print()

    async def _swarm_chat(self, goal: str) -> None:
        """Execute a goal using the multi-agent swarm."""
        self._console.print()
        self._console.print(Panel(f"[bold]Goal:[/] {goal}", style="magenta", expand=False))

        try:
            async for update in self._swarm.execute_goal(goal):
                if update.update_type == "status":
                    self._console.print(f"  [dim cyan]{update.content}[/dim cyan]")
                elif update.update_type == "task_done":
                    self._console.print(f"  [green]{update.content}[/green]")
                elif update.update_type == "error":
                    self._console.print(f"  [bold red]{update.content}[/bold red]")
                elif update.update_type == "result":
                    self._console.print()
                    self._console.print(Panel(
                        Markdown(update.content),
                        title="[bold]Swarm Result[/bold]",
                        style="green",
                        expand=True,
                    ))

            self._memory.add_message(
                self._session_id,
                Message(role="user", content=f"[SWARM GOAL] {goal}"),
            )
            self._memory.add_message(
                self._session_id,
                Message(role="assistant", content=f"[Swarm executed goal: {goal}]"),
            )

        except Exception as e:
            self._console.print(f"\n[bold red]Swarm Error:[/] {e}")
            logger.exception("Swarm execution error")

        self._console.print()

    async def _handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns True if should quit."""
        parts = cmd.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("/quit", "/exit", "/q"):
            self._console.print("[dim]Goodbye![/dim]")
            return True

        elif command == "/help":
            self._console.print(
                Panel(
                    "[bold]/help[/]        — Show this help\n"
                    "[bold]/clear[/]       — Clear conversation history\n"
                    "[bold]/memory[/]      — Show memory stats (all layers)\n"
                    "[bold]/consolidate[/] — Trigger memory consolidation now\n"
                    "[bold]/agents[/]      — Show agent swarm status\n"
                    "[bold]/swarm[/]       — Toggle swarm mode (multi-agent)\n"
                    "[bold]/skills[/]      — List available skills\n"
                    "[bold]/invoke[/]      — Invoke a skill: /invoke <skill> <params>\n"
                    "[bold]/model[/]       — Show current LLM provider info\n"
                    "[bold]/quit[/]        — Exit NEXUS",
                    title="NEXUS Commands",
                    style="cyan",
                )
            )

        elif command == "/clear":
            self._memory.clear_session(self._session_id)
            self._memory.add_message(
                self._session_id,
                Message(role="system", content=SYSTEM_PROMPT),
            )
            self._console.print("[dim]Conversation cleared.[/dim]")

        elif command == "/memory":
            msgs = self._memory.get_messages(self._session_id)
            stats = await self._memory.stats()
            lines = [
                f"Working memory: {len(msgs)} messages",
                f"Active sessions: {stats.get('working_sessions', 0)}",
            ]
            if "episodic_count" in stats:
                lines.append(f"Episodic memories: {stats['episodic_count']}")
            if "semantic_count" in stats:
                lines.append(f"Semantic knowledge: {stats['semantic_count']}")
            if "consolidation_running" in stats:
                lines.append(f"Consolidation: {'running' if stats['consolidation_running'] else 'stopped'}")
                lines.append(f"Consolidation cycles: {stats.get('consolidation_cycles', 0)}")
            self._console.print(
                Panel("\n".join(lines), title="Memory Stats", style="blue")
            )

        elif command == "/consolidate":
            self._console.print("[dim]Running memory consolidation...[/dim]")
            created = await self._memory.consolidate_now()
            self._console.print(f"[green]Consolidation complete: {created} knowledge entries created[/green]")

        elif command == "/model":
            providers = self._router.available_providers
            self._console.print(
                Panel(
                    f"Available: {', '.join(providers)}",
                    title="LLM Providers",
                    style="magenta",
                )
            )

        elif command == "/swarm":
            if not self._swarm:
                self._console.print("[yellow]Swarm not initialized (no LLM providers?)[/yellow]")
            else:
                self._swarm_mode = not self._swarm_mode
                if self._swarm_mode:
                    self._console.print(
                        "[bold magenta]Swarm mode ON[/] — your messages are now "
                        "goals that the multi-agent swarm will decompose and execute."
                    )
                else:
                    self._console.print(
                        "[dim]Swarm mode OFF — back to direct chat.[/dim]"
                    )

        elif command == "/agents":
            if not self._swarm:
                self._console.print("[dim]Swarm not initialized.[/dim]")
            else:
                summary = self._swarm.status_summary()
                self._console.print(Panel(summary, title="Swarm Status", style="magenta"))

        elif command == "/skills":
            if not self._skills:
                self._console.print("[dim]No skills loaded.[/dim]")
            else:
                table = Table(title="Available Skills", style="cyan")
                table.add_column("Name", style="bold")
                table.add_column("Description")
                table.add_column("Capabilities", style="dim")

                for name in self._skills.list_skills():
                    skill = self._skills.get(name)
                    caps = ", ".join(c.value for c in skill.manifest.capabilities_required)
                    table.add_row(name, skill.manifest.description, caps or "none")

                self._console.print(table)

        elif command == "/invoke":
            await self._invoke_skill(args)

        else:
            self._console.print(f"[yellow]Unknown command: {command}[/yellow]")

        return False

    async def _invoke_skill(self, args: str) -> None:
        """Invoke a skill from the CLI: /invoke <skill_name> <json_params>"""
        if not self._skills:
            self._console.print("[yellow]No skills loaded.[/yellow]")
            return

        parts = args.split(maxsplit=1)
        if not parts:
            self._console.print("[yellow]Usage: /invoke <skill_name> [json_params][/yellow]")
            return

        skill_name = parts[0]
        params_str = parts[1] if len(parts) > 1 else "{}"

        try:
            import json
            params = json.loads(params_str)
        except json.JSONDecodeError:
            params = {"input": params_str}

        try:
            result = await self._skills.invoke(skill_name, params, actor="user")
            if result.success:
                self._console.print(Panel(
                    str(result.output),
                    title=f"[green]{skill_name}[/green]",
                    style="green",
                ))
            else:
                self._console.print(f"[red]Skill error: {result.error}[/red]")
        except Exception as e:
            self._console.print(f"[bold red]Error invoking {skill_name}:[/] {e}")
