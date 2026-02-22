<p align="center">
  <a href="https://github.com/tushark01/NEXUS"><img src="https://img.shields.io/github/stars/tushark01/NEXUS?style=for-the-badge&logo=github&color=yellow" /></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/version-0.1.0-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/agents-multi--swarm-ff6b6b?style=for-the-badge" />
  <a href="https://github.com/tushark01/NEXUS/issues"><img src="https://img.shields.io/github/issues/tushark01/NEXUS?style=for-the-badge&color=orange" /></a>
</p>

```
    _   _  _____  __  __  _   _  ____
   | \ | || ____|\ \/ / | | | |/ ___|
   |  \| ||  _|   \  /  | | | |\___ \
   | |\  || |___  /  \  | |_| | ___) |
   |_| \_||_____|/_/\_\  \___/ |____/
```

# NEXUS — Network of Evolving eXpert Unified Systems

> A next-generation, security-first AI agent framework with multi-agent swarm intelligence, tri-layer self-improving memory, and pluggable skill architecture. Built to surpass what came before.
>

![1771744999206](image/README/1771744999206.png)

---

## Table of Contents

- [Why NEXUS?](#why-nexus)
- [NEXUS vs OpenClaw](#nexus-vs-openclaw--why-we-exist)
- [Architecture Overview](#architecture-overview)
- [Features at a Glance](#features-at-a-glance)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [Swarm Mode](#swarm-mode--multi-agent-intelligence)
- [Tri-Layer Memory System](#tri-layer-memory-system)
- [Skills &amp; Plugin System](#skills--plugin-system)
- [Web Dashboard &amp; REST API](#web-dashboard--rest-api)
- [Security Architecture](#security-architecture)
- [LLM Provider Routing](#llm-provider-routing)
- [Project Structure](#project-structure)
- [Deployment on AWS](#deployment-on-aws)
- [Development Guide](#development-guide)
- [Roadmap](#roadmap)
- [License](#license)

---

## Why NEXUS?

Most AI agent frameworks are glorified prompt wrappers. They chain LLM calls, call it "agentic", and ship it with zero security, no memory beyond the context window, and a single-agent bottleneck. NEXUS is built differently.

**NEXUS is what happens when you design an agent framework from scratch with three non-negotiable principles:**

1. **Security is not optional** — Every skill runs in a sandbox. Every action is audit-logged. Every capability is explicitly granted. No agent can access anything it wasn't designed to touch.
2. **Agents are a swarm, not a singleton** — A Coordinator evaluates your goal. A Planner decomposes it into a DAG. Researchers, Executors, and Critics run in parallel. A consensus engine resolves disagreements. One goal, many minds.
3. **Memory evolves** — Working memory holds your conversation. Episodic memory records every interaction with importance scores. Semantic memory crystallizes patterns into long-term knowledge. A consolidation loop connects them all.

---

## NEXUS vs OpenClaw — Why We Exist

| Dimension                    | OpenClaw                                                    | NEXUS                                                                                                   |
| ---------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Security**           | Flat permissions, no sandboxing, skills can access anything | Capability-based ACL, subprocess sandboxing, blocked-module lists, full audit trail                     |
| **Agent Architecture** | Single-agent with tool calls                                | Multi-agent swarm (Coordinator, Planner, Executor, Researcher, Critic) with parallel DAG execution      |
| **Memory**             | Conversation buffer only                                    | Tri-layer: Working + Episodic (vector-indexed) + Semantic (LLM-consolidated knowledge)                  |
| **Consensus**          | None — single agent decides everything                     | 4 strategies: Majority, Supermajority, Unanimous, Confidence-Weighted voting                            |
| **Skill Security**     | Skills self-declare safety, no enforcement                  | Skills must declare capabilities; enforcer checks at runtime; sandbox isolates execution                |
| **Audit**              | Minimal logging                                             | Append-only JSONL audit log for every capability check, skill invocation, and security event            |
| **LLM Support**        | Typically single provider                                   | Multi-provider (Claude, GPT, Ollama) with complexity-based routing and automatic fallback chains        |
| **Interfaces**         | Usually just CLI or API                                     | CLI + FastAPI Dashboard + WebSocket streaming + Telegram + Discord (planned)                            |
| **Rate Limiting**      | None                                                        | Token-bucket rate limiter per key with burst support                                                    |
| **Code Execution**     | Direct `exec()`                                           | Subprocess sandbox with blocked imports, timeout enforcement, and resource limits                       |
| **Error Recovery**     | Crash or retry                                              | DAG-based: failed tasks are isolated, remaining tasks continue, Coordinator synthesizes partial results |

**The core lesson from OpenClaw:** shipping an agent framework without security-by-design is shipping a liability. NEXUS makes security the foundation, not an afterthought.

---

## Architecture Overview

```
                          +---------------------+
                          |     USER INPUT       |
                          | (CLI / API / WebSocket / Telegram / Discord)
                          +----------+----------+
                                     |
                          +----------v----------+
                          |    COORDINATOR       |
                          | Evaluates complexity |
                          | Strategy: direct or  |
                          | swarm                |
                          +----+----------+-----+
                               |          |
                    Simple     |          |  Complex
                               |          |
                    +----------v+    +----v--------+
                    | Direct LLM |   |   PLANNER   |
                    | Response   |   | Decomposes  |
                    +------------+   | into TaskDAG|
                                     +------+------+
                                            |
                            +---------------+---------------+
                            |               |               |
                     +------v------+ +------v------+ +------v------+
                     |  RESEARCHER | |  EXECUTOR   | |  EXECUTOR   |
                     |  (parallel) | |  (parallel) | |  (parallel) |
                     +------+------+ +------+------+ +------+------+
                            |               |               |
                            +-------+-------+-------+-------+
                                    |               |
                             +------v------+ +------v------+
                             |   CRITIC    | | COORDINATOR |
                             |   Reviews   | | Synthesizes |
                             +-------------+ +------+------+
                                                    |
                                          +---------v---------+
                                          |   FINAL RESPONSE  |
                                          +-------------------+

    +------------------+  +------------------+  +------------------+
    |  WORKING MEMORY  |  | EPISODIC MEMORY  |  | SEMANTIC MEMORY  |
    |  (conversation)  |  | (vector-indexed  |  | (consolidated    |
    |                  |  |  experiences)    |  |  knowledge)      |
    +--------+---------+  +--------+---------+  +--------+---------+
             |                     |                     ^
             |                     |    CONSOLIDATION    |
             |                     +-----LOOP-----------+
             |                    (LLM extracts patterns)
             +--------------------------------------------+

    +------------------------------------------------------------------+
    |                     SECURITY LAYER                                |
    |  [Capability Enforcer] [Sandbox] [Audit Logger] [Rate Limiter]   |
    +------------------------------------------------------------------+
```

---

## Features at a Glance

### Multi-Agent Swarm

- **5 specialized agent roles**: Coordinator, Planner, Executor, Researcher, Critic
- **TaskDAG**: Directed acyclic graph with dependency tracking and parallel wave execution
- **Message Bus**: Agent-to-agent messaging, broadcast, topic-based pub/sub, dead letter queue
- **Consensus Engine**: 4 voting strategies for agent disagreements
- **Agent Pool**: Dynamic spawning, lifecycle management, concurrency limits

### Tri-Layer Memory

- **Working Memory**: Per-session conversation buffer with sliding window eviction
- **Episodic Memory**: Vector-indexed (ChromaDB) interaction store with importance scoring
- **Semantic Memory**: Long-term knowledge categorized as facts, patterns, preferences, procedures
- **Consolidation Loop**: Background LLM task that extracts patterns from episodes into knowledge

### Security-First Design

- **Capability-Based ACL**: Skills declare required capabilities; enforcer checks at runtime
- **Subprocess Sandboxing**: Code executes in isolated processes with blocked imports and timeouts
- **Cryptographic Audit Trail**: Append-only JSONL log of every security event
- **Token Bucket Rate Limiting**: Per-key rate limiting with burst support
- **Constraint System**: Path globs, domain allowlists, command whitelists on capabilities

### Smart LLM Routing

- **Multi-Provider**: Anthropic Claude, OpenAI GPT, Ollama (local) — all via unified interface
- **Complexity-Based Routing**: Simple tasks go to fast models, complex tasks go to powerful ones
- **Automatic Fallback Chains**: If Claude fails, fall back to GPT (and vice versa)
- **Streaming Support**: Async streaming for all providers with real-time token output

### 5 Built-in Skills

- **Web Search**: DuckDuckGo integration for real-time information retrieval
- **File Operations**: Read, write, list, and delete files (capability-gated)
- **Shell Execution**: Run shell commands (sandboxed, command-whitelisted)
- **Code Execution**: Run Python code in isolated subprocesses
- **Notes**: Persistent note-taking for cross-session context

### Multiple Interfaces

- **Rich CLI**: Beautiful terminal with Markdown rendering, streaming, swarm mode toggle
- **FastAPI Dashboard**: Dark-themed web UI with real-time chat, system stats, skill management
- **WebSocket Streaming**: Real-time token-by-token streaming for web clients
- **REST API**: Full CRUD for chat, swarm execution, skills, and memory
- **Telegram & Discord**: Bot interfaces (planned)

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- At least one LLM API key (Anthropic or OpenAI), or Ollama running locally

### Installation

```bash
# Clone the repository
git clone https://github.com/tushark01/NEXUS.git
cd NEXUS

# Install core dependencies
pip install -e .

# Or install everything (API dashboard, Telegram, Discord, Ollama)
pip install -e ".[all]"

# Or install specific extras
pip install -e ".[api]"       # FastAPI web dashboard
pip install -e ".[dev]"       # Testing & linting tools
```

### Configure

```bash
# Copy the example config
cp .env.example .env

# Edit with your API keys
nano .env
```

At minimum, set one of:

```env
NEXUS_ANTHROPIC_API_KEY=sk-ant-your-key-here
# or
NEXUS_OPENAI_API_KEY=sk-your-key-here
```

### Launch the CLI

```bash
# Start the interactive terminal
nexus

# Or run directly
python -m nexus
```

### Launch the Web Dashboard

```bash
# Start the FastAPI server (requires api extra)
nexus-server

# Then open http://127.0.0.1:8000 in your browser
```

---

## Configuration

NEXUS uses environment variables with the `NEXUS_` prefix. All configuration is managed through Pydantic Settings with `.env` file support.

### Environment Variables

| Variable                    | Default                      | Description                                                  |
| --------------------------- | ---------------------------- | ------------------------------------------------------------ |
| `NEXUS_ANTHROPIC_API_KEY` | —                           | Anthropic API key for Claude models                          |
| `NEXUS_OPENAI_API_KEY`    | —                           | OpenAI API key for GPT models                                |
| `NEXUS_DEFAULT_PROVIDER`  | `anthropic`                | Default LLM provider (`anthropic`, `openai`, `ollama`) |
| `NEXUS_ANTHROPIC_MODEL`   | `claude-sonnet-4-20250514` | Default Anthropic model                                      |
| `NEXUS_OPENAI_MODEL`      | `gpt-4o`                   | Default OpenAI model                                         |
| `NEXUS_OLLAMA_BASE_URL`   | `http://localhost:11434`   | Ollama server URL                                            |
| `NEXUS_OLLAMA_MODEL`      | `llama3`                   | Default Ollama model                                         |

#### Memory Configuration

| Variable                         | Default              | Description                               |
| -------------------------------- | -------------------- | ----------------------------------------- |
| `NEXUS_MEMORY_CHROMA_DIR`      | `./data/chroma`    | ChromaDB persistence directory            |
| `NEXUS_MEMORY_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model for embeddings |

#### Security Configuration

| Variable                           | Default                | Description                                     |
| ---------------------------------- | ---------------------- | ----------------------------------------------- |
| `NEXUS_SECURITY_SANDBOX_ENABLED` | `true`               | Enable subprocess sandboxing for code execution |
| `NEXUS_SECURITY_AUDIT_LOG`       | `./data/audit.jsonl` | Path to the append-only audit log               |

#### Interface Configuration

| Variable                 | Default       | Description                 |
| ------------------------ | ------------- | --------------------------- |
| `NEXUS_API_HOST`       | `127.0.0.1` | FastAPI server bind address |
| `NEXUS_API_PORT`       | `8000`      | FastAPI server port         |
| `NEXUS_TELEGRAM_TOKEN` | —            | Telegram bot token          |
| `NEXUS_DISCORD_TOKEN`  | —            | Discord bot token           |

---

## CLI Commands

Once `nexus` is running, you have access to these commands:

| Command                      | Description                                                         |
| ---------------------------- | ------------------------------------------------------------------- |
| `/help`                    | Show all available commands                                         |
| `/swarm`                   | Toggle swarm mode — messages become multi-agent goals              |
| `/agents`                  | Show live swarm status (agents, message bus, consensus)             |
| `/skills`                  | List all loaded skills in a formatted table                         |
| `/invoke <skill> <params>` | Invoke a skill directly (e.g.,`/invoke notes {"action": "list"}`) |
| `/memory`                  | Show tri-layer memory statistics                                    |
| `/consolidate`             | Trigger immediate memory consolidation (episodic -> semantic)       |
| `/model`                   | Show active LLM providers                                           |
| `/clear`                   | Clear conversation history                                          |
| `/quit`                    | Exit NEXUS                                                          |

### Normal Mode

Type natural language and chat directly with the LLM (streaming Markdown output).

### Swarm Mode (`/swarm`)

Your messages become **goals** that the entire agent swarm works on:

1. Coordinator evaluates complexity
2. Planner decomposes into parallel tasks
3. Researchers and Executors run concurrently
4. Critic reviews results
5. Coordinator synthesizes the final answer

---

## Swarm Mode — Multi-Agent Intelligence

NEXUS doesn't just call an LLM. It deploys a swarm.

### How It Works

```
You: "Research the latest trends in quantum computing and write a summary report"

Coordinator: Strategy = SWARM (complex, multi-step goal)

Planner decomposes into TaskDAG:
  [x] t1: Research quantum computing breakthroughs 2024-2025 (researcher)
  [x] t2: Research quantum computing industry applications (researcher)
  [x] t3: Analyze trends and identify patterns (executor, depends: t1, t2)
  [x] t4: Write structured summary report (executor, depends: t3)
  [x] t5: Review report quality and accuracy (critic, depends: t4)

Tasks t1 and t2 run IN PARALLEL (no dependencies).
Task t3 waits for both, then runs.
Task t4 uses t3's output.
Critic reviews. Coordinator synthesizes.
```

### Agent Roles

| Role                  | Purpose                                                                    | When Used                   |
| --------------------- | -------------------------------------------------------------------------- | --------------------------- |
| **Coordinator** | Evaluates goals, decides strategy, synthesizes results, resolves conflicts | Always (swarm brain)        |
| **Planner**     | Decomposes goals into a TaskDAG with dependencies and role assignments     | Complex goals               |
| **Researcher**  | Gathers and synthesizes information on topics                              | Information-gathering tasks |
| **Executor**    | Carries out specific tasks — writing, analysis, computation               | Action/creation tasks       |
| **Critic**      | Reviews output for accuracy, completeness, and quality                     | Quality validation          |

### Consensus Engine

When agents disagree or when decisions need collective agreement, the consensus engine supports:

- **Majority**: > 50% approve
- **Supermajority**: >= 66.7% approve
- **Unanimous**: All must approve
- **Weighted**: Confidence-weighted voting (agents with higher confidence count more)

---

## Tri-Layer Memory System

NEXUS remembers. Not just the current conversation — it learns from every interaction.

### Layer 1: Working Memory

- **What**: Current conversation context per session
- **How**: Sliding window buffer that preserves system prompts
- **Lifespan**: Session duration
- **Example**: The last 50 messages in your CLI chat

### Layer 2: Episodic Memory

- **What**: Every interaction, event, and task result, indexed by semantic similarity
- **How**: ChromaDB vector store with sentence-transformer embeddings
- **Lifespan**: Persistent across sessions
- **Features**: Importance scoring, type categorization, similarity-based recall
- **Example**: "Last week, the user asked about Kubernetes deployment and preferred Helm charts"

### Layer 3: Semantic Memory

- **What**: Long-term knowledge distilled from patterns across many episodes
- **How**: LLM-powered consolidation extracts durable facts, preferences, and procedures
- **Lifespan**: Permanent (until invalidated)
- **Categories**: `fact`, `pattern`, `preference`, `procedure`, `general`
- **Example**: "The user prefers TypeScript over JavaScript" (extracted from 12 episodes)

### Consolidation Loop

A background task periodically:

1. Fetches high-importance episodic memories
2. Passes them through an LLM to identify patterns
3. Stores extracted knowledge in semantic memory
4. Builds context from both layers for future prompts

Trigger manually with `/consolidate` in the CLI or `POST /memory/consolidate` via API.

---

## Skills & Plugin System

Skills are the hands of NEXUS — they let agents interact with the real world.

### Built-in Skills

| Skill          | Description                     | Capabilities Required         |
| -------------- | ------------------------------- | ----------------------------- |
| `web_search` | Search the web via DuckDuckGo   | `network:http`              |
| `file_ops`   | Read, write, list, delete files | `file:read`, `file:write` |
| `shell`      | Execute shell commands          | `shell:execute`             |
| `code_exec`  | Run Python code in sandbox      | `shell:execute`             |
| `notes`      | Persistent note-taking          | `file:read`, `file:write` |

### Invoking Skills

From the CLI:

```
/invoke web_search {"query": "latest AI news"}
/invoke notes {"action": "create", "title": "Meeting Notes", "content": "..."}
/invoke file_ops {"action": "read", "path": "./data/config.yaml"}
```

From the API:

```bash
curl -X POST http://localhost:8000/skills/invoke \
  -H "Content-Type: application/json" \
  -d '{"skill_name": "web_search", "params": {"query": "quantum computing"}}'
```

### Creating Custom Skills

```python
from nexus.skills.base import BaseSkill, ParameterDef, SkillManifest, SkillResult
from nexus.security.capabilities import Capability

class MySkill(BaseSkill):
    manifest = SkillManifest(
        name="my_custom_skill",
        version="1.0.0",
        description="Does something amazing",
        capabilities_required=[Capability.NETWORK_HTTP],
        parameters={
            "url": ParameterDef(type="string", description="Target URL", required=True),
        },
    )

    async def execute(self, params: dict) -> SkillResult:
        url = params["url"]
        # Your skill logic here
        return SkillResult(success=True, output=f"Processed {url}")
```

Skills auto-generate LLM tool definitions from their manifests, so agents can use them natively.

---

## Web Dashboard & REST API

### Dashboard

Launch with `nexus-server` and open `http://127.0.0.1:8000`:

- **Real-time chat** with WebSocket streaming (token-by-token output)
- **System info panel** — providers, version, active skills, swarm status
- **Memory stats** — live working/episodic/semantic counts and consolidation status
- **Skills browser** — all loaded skills with descriptions
- **Swarm monitor** — agent pool status, message bus metrics
- **Dark theme** with gradient accents — looks stunning

### REST API Endpoints

| Method   | Endpoint                | Description                              |
| -------- | ----------------------- | ---------------------------------------- |
| `GET`  | `/health`             | Health check                             |
| `GET`  | `/info`               | System info (providers, skills, version) |
| `POST` | `/chat`               | Send a message and get a response        |
| `WS`   | `/ws/chat`            | WebSocket streaming chat                 |
| `POST` | `/swarm/execute`      | Execute a goal via the swarm             |
| `GET`  | `/swarm/status`       | Get swarm status summary                 |
| `GET`  | `/skills`             | List all skills with parameters          |
| `POST` | `/skills/invoke`      | Invoke a skill                           |
| `GET`  | `/memory/stats`       | Memory statistics across all layers      |
| `POST` | `/memory/consolidate` | Trigger memory consolidation             |

### Example: Chat via API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain quantum entanglement simply", "session_id": "user1"}'
```

### Example: Swarm Execution via API

```bash
curl -X POST http://localhost:8000/swarm/execute \
  -H "Content-Type: application/json" \
  -d '{"goal": "Research and compare the top 3 Python web frameworks for 2025"}'
```

---

## Security Architecture

NEXUS was designed with security as a foundational pillar — not bolted on.

### Capability-Based Access Control

Every skill declares what it needs. The enforcer checks at runtime.

```python
# A skill declares:
capabilities_required = [Capability.FILE_READ, Capability.NETWORK_HTTP]

# The enforcer can add constraints:
CapabilityGrant(
    capability=Capability.FILE_READ,
    constraints={"paths": ["/tmp/nexus/*", "~/documents/*"]}
)
CapabilityGrant(
    capability=Capability.NETWORK_HTTP,
    constraints={"domains": ["api.github.com", "api.openai.com"]}
)
```

**9 capability types**: `file:read`, `file:write`, `network:http`, `network:websocket`, `shell:execute`, `memory:read`, `memory:write`, `llm:invoke`, `system:info`

### Subprocess Sandboxing

Code execution runs in an isolated subprocess with:

- **Blocked imports**: `subprocess`, `shutil`, `ctypes`, `socket`, `http`, `urllib`, and more
- **Timeout enforcement**: Configurable (default 30s), process killed on timeout
- **Resource isolation**: Separate process with restricted namespace
- **JSON I/O**: Communication via stdin/stdout, no shared memory

### Audit Logging

Every security-relevant event is logged to an append-only JSONL file:

```json
{"timestamp": "2025-01-15T10:30:00Z", "event_type": "skill_invocation", "actor": "executor_a1b2c3", "action": "invoke:shell", "resource": "shell", "result": "allowed", "details": {"params": {"command": "ls -la"}}}
```

### Rate Limiting

Token-bucket rate limiter prevents abuse:

- Configurable rate (tokens per second) and burst size
- Per-key limiting (per user, per agent, per skill)
- Async-friendly with `await limiter.wait(key)`

---

## LLM Provider Routing

### Supported Providers

| Provider            | Models                                   | Features             |
| ------------------- | ---------------------------------------- | -------------------- |
| **Anthropic** | Claude Opus 4.6, Sonnet 4.6, Haiku 4.5   | Streaming, tool use  |
| **OpenAI**    | GPT-4o, GPT-4o-mini, o1                  | Streaming, tool use  |
| **Ollama**    | Llama 3, Mistral, Phi-3, any local model | Local, private, free |

### Complexity-Based Routing

The router selects providers based on task complexity hints:

```python
# Simple tasks -> fastest/cheapest model
await router.complete(request, hint=TaskComplexity.SIMPLE)

# Complex tasks -> most capable model
await router.complete(request, hint=TaskComplexity.COMPLEX)
```

### Automatic Fallback

If Anthropic is configured as primary and OpenAI as secondary:

```
Claude rate limited? -> Automatically falls back to GPT-4o
GPT-4o down? -> Automatically falls back to Claude
Both down? -> Clear error message
```

---

## Project Structure

```
nexus/
├── pyproject.toml                    # Project config, dependencies, scripts
├── .env.example                      # Configuration template
├── README.md                         # This file
│
├── src/nexus/
│   ├── app.py                        # CLI entry point & bootstrap
│   ├── server.py                     # Web server entry point
│   ├── __main__.py                   # python -m nexus support
│   │
│   ├── agents/                       # Multi-agent swarm system
│   │   ├── base.py                   #   Abstract BaseAgent, roles, states, messaging
│   │   ├── coordinator.py            #   Swarm brain — strategy, synthesis, conflict resolution
│   │   ├── planner.py                #   Goal decomposition into TaskDAGs
│   │   ├── executor.py               #   Task execution agent
│   │   ├── researcher.py             #   Information gathering agent
│   │   ├── critic.py                 #   Quality review agent
│   │   ├── orchestrator.py           #   Master conductor — parallel DAG execution
│   │   ├── pool.py                   #   Agent lifecycle & pool management
│   │   ├── task.py                   #   Task model & DAG with dependency tracking
│   │   ├── message_bus.py            #   Inter-agent communication system
│   │   └── consensus.py              #   Voting & agreement engine
│   │
│   ├── core/                         # Framework fundamentals
│   │   ├── config.py                 #   Pydantic settings with env/YAML loading
│   │   ├── event_bus.py              #   Async pub/sub event system
│   │   ├── events.py                 #   Typed event hierarchy
│   │   ├── lifecycle.py              #   Ordered startup/shutdown
│   │   ├── registry.py               #   Lightweight dependency injection
│   │   └── errors.py                 #   Exception hierarchy
│   │
│   ├── llm/                          # LLM abstraction layer
│   │   ├── router.py                 #   Intelligent provider routing + fallbacks
│   │   ├── base.py                   #   LLMProvider abstract base
│   │   ├── schemas.py                #   Request/response types
│   │   └── providers/
│   │       ├── anthropic.py          #   Claude API integration
│   │       └── openai.py             #   OpenAI API integration
│   │
│   ├── memory/                       # Tri-layer memory system
│   │   ├── manager.py                #   Unified facade for all layers
│   │   ├── working.py                #   Session-based conversation buffer
│   │   ├── episodic.py               #   Vector-indexed interaction store
│   │   ├── semantic.py               #   Consolidated long-term knowledge
│   │   ├── consolidation.py          #   Background episodic->semantic loop
│   │   ├── store.py                  #   VectorStore protocol + ChromaDB impl
│   │   └── embeddings.py             #   Sentence transformer embeddings
│   │
│   ├── security/                     # Security infrastructure
│   │   ├── capabilities.py           #   Capability-based ACL system
│   │   ├── sandbox.py                #   Subprocess execution sandbox
│   │   ├── audit.py                  #   Append-only JSONL audit logger
│   │   ├── rate_limiter.py           #   Token bucket rate limiter
│   │   └── policies.py               #   Security policy definitions
│   │
│   ├── skills/                       # Plugin/skill system
│   │   ├── base.py                   #   BaseSkill, SkillManifest, SkillResult
│   │   ├── registry.py               #   Skill discovery & security-enforced invocation
│   │   ├── loader.py                 #   Dynamic skill loading from paths
│   │   └── builtin/
│   │       ├── web_search.py         #   DuckDuckGo web search
│   │       ├── file_ops.py           #   File CRUD operations
│   │       ├── shell.py              #   Shell command execution
│   │       ├── code_exec.py          #   Python code execution
│   │       └── notes.py              #   Persistent note-taking
│   │
│   └── interfaces/                   # User-facing interfaces
│       ├── cli/
│       │   └── app.py                #   Rich terminal with swarm + skills
│       └── api/
│           └── app.py                #   FastAPI dashboard + REST + WebSocket
│
└── tests/
    ├── conftest.py                   # Shared fixtures
    └── unit/
        ├── test_task_dag.py          # TaskDAG dependency resolution
        ├── test_event_bus.py         # Async pub/sub system
        ├── test_working_memory.py    # Conversation buffer
        ├── test_consensus.py         # All 4 voting strategies
        ├── test_message_bus.py       # Agent messaging
        ├── test_capabilities.py      # ACL & constraint enforcement
        └── test_config.py            # Configuration loading
```

---

## Deployment on AWS

### Option 1: EC2 (Simple)

```bash
# 1. Launch an EC2 instance (t3.medium+ recommended)
#    - Ubuntu 22.04 LTS
#    - Security group: allow ports 22 (SSH) and 8000 (Dashboard)

# 2. SSH in and install dependencies
sudo apt update && sudo apt install -y python3.11 python3.11-venv git

# 3. Clone and setup
git clone https://github.com/tushark01/NEXUS.git
cd NEXUS
python3.11 -m venv venv
source venv/bin/activate
pip install -e ".[api]"

# 4. Configure
cp .env.example .env
nano .env  # Add your API keys, set NEXUS_API_HOST=0.0.0.0

# 5. Run with systemd (production)
sudo tee /etc/systemd/system/nexus.service << 'EOF'
[Unit]
Description=NEXUS AI Agent Framework
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/NEXUS
Environment=PATH=/home/ubuntu/NEXUS/venv/bin
ExecStart=/home/ubuntu/NEXUS/venv/bin/nexus-server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable nexus && sudo systemctl start nexus
```

### Option 2: ECS Fargate (Containerized)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -e ".[api]"

EXPOSE 8000

CMD ["nexus-server"]
```

```bash
# Build and push to ECR
aws ecr create-repository --repository-name nexus
docker build -t nexus .
docker tag nexus:latest <account>.dkr.ecr.<region>.amazonaws.com/nexus:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/nexus:latest

# Create ECS task definition and service
# Set environment variables in task definition:
#   NEXUS_ANTHROPIC_API_KEY (from Secrets Manager)
#   NEXUS_API_HOST=0.0.0.0
#   NEXUS_API_PORT=8000
```

### Option 3: Lambda + API Gateway (Serverless)

For the REST API only (no WebSocket/swarm):

```bash
# Using Mangum adapter for Lambda
pip install mangum

# In your Lambda handler:
from mangum import Mangum
from nexus.interfaces.api.app import create_api

app = create_api(router=router, memory=memory, swarm=swarm, skills=skills)
handler = Mangum(app)
```

### Production Recommendations

| Concern               | Recommendation                                                             |
| --------------------- | -------------------------------------------------------------------------- |
| **API Keys**    | Store in AWS Secrets Manager, inject as env vars                           |
| **Persistence** | Mount EBS volume for ChromaDB data at `/app/data`                        |
| **HTTPS**       | Use ALB with ACM certificate in front of the service                       |
| **Monitoring**  | CloudWatch logs + metrics, set alerts on error rates                       |
| **Scaling**     | ECS auto-scaling based on CPU/memory, or use Fargate Spot for cost savings |
| **Networking**  | Run in private subnet with NAT Gateway for outbound LLM API calls          |
| **Memory**      | For large-scale deployments, replace ChromaDB with Pinecone or Weaviate    |

---

## Development Guide

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev,api]"

# Run tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_consensus.py

# Lint
ruff check src/

# Type check
mypy src/nexus/
```

### Running Tests

```bash
# All unit tests
pytest tests/unit/

# With coverage (install pytest-cov first)
pytest --cov=nexus tests/

# Just the fast tests (no LLM calls)
pytest tests/unit/ -x --tb=short
```

### Code Style

- **Formatter**: Ruff (line length 100)
- **Linting**: Ruff with E, F, I, N, W, UP rules
- **Type Checking**: mypy strict mode
- **Python**: 3.11+ with full type annotations
- **Async**: All I/O operations are async

---

## Use Cases

### Personal AI Assistant

Run `nexus` locally with Ollama for a private, offline AI assistant that remembers your preferences across sessions.

### Research Automation

Use swarm mode: "Research the current state of CRISPR gene therapy, analyze the top 5 recent papers, and produce a summary with key findings."

### Code Generation Pipeline

Planner decomposes a feature spec -> Researchers gather API docs -> Executors write code -> Critic reviews for bugs.

### Knowledge Management

The tri-layer memory turns NEXUS into a personal knowledge base that gets smarter over time. Ask it something in January, and it remembers the context in March.

### Team Chatbot

Deploy the web dashboard for your team. Each person gets their own session with persistent memory. Skills let the bot query internal APIs, databases, and documentation.

### Security-Audited Automation

Every action is logged. Every capability is explicitly granted. Use NEXUS for automation tasks where you need a clear audit trail of what the AI did and why.

---

## Roadmap

### v0.2.0 — Interfaces

- [ ] Telegram bot interface
- [ ] Discord bot interface
- [ ] Slack integration
- [ ] Voice input/output via Whisper + TTS

### v0.3.0 — Advanced Skills

- [ ] Ollama provider integration
- [ ] Database query skill (PostgreSQL, SQLite)
- [ ] API builder skill (generate REST endpoints)
- [ ] Image generation skill (DALL-E, Stable Diffusion)
- [ ] RAG skill (document ingestion + retrieval)

### v0.4.0 — Intelligence

- [ ] Self-improving agent prompts (based on critic feedback)
- [ ] Automatic skill discovery and composition
- [ ] Multi-swarm coordination (swarms of swarms)
- [ ] Reinforcement learning from human feedback (RLHF) for agent behavior

### v1.0.0 — Production

- [ ] Kubernetes Helm chart
- [ ] Prometheus metrics exporter
- [ ] Admin dashboard with user management
- [ ] Plugin marketplace
- [ ] End-to-end encryption for memory storage

---

## Stats

```
Language:     Python 3.11+
Files:        70 Python source files
Lines:        5,750+ lines of code
Tests:        7 test suites, 50+ test cases
Agents:       5 specialized roles
Skills:       5 built-in
Memory:       3 layers + consolidation
Providers:    3 LLM providers
Interfaces:   2 (CLI + Web Dashboard)
Security:     4 enforcement layers
Consensus:    4 voting strategies
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

Created by [Tushar](https://github.com/tushark01) | Repository: [github.com/tushark01/NEXUS](https://github.com/tushark01/NEXUS)

---

<p align="center">
  <b>Built with obsessive attention to security, architecture, and intelligence.</b><br>
  <i>NEXUS doesn't just respond — it thinks, collaborates, remembers, and evolves.</i>
</p>
