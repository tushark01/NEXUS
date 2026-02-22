"""NEXUS FastAPI application — REST API + WebSocket streaming + web dashboard."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "web"


class GoalRequest(BaseModel):
    goal: str
    context: str = ""


class SkillInvokeRequest(BaseModel):
    skill_name: str
    params: dict[str, Any] = {}


def create_api(
    router: Any,  # ModelRouter
    memory: Any,  # MemoryManager
    swarm: Any | None = None,  # SwarmOrchestrator
    skills: Any | None = None,  # SkillRegistry
) -> FastAPI:
    """Create the NEXUS FastAPI application."""
    app = FastAPI(
        title="NEXUS API",
        description="Network of Evolving eXpert Unified Systems",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health & info ---

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/info")
    async def info():
        return {
            "name": "NEXUS",
            "version": "0.1.0",
            "providers": router.available_providers,
            "skills": skills.list_skills() if skills else [],
            "swarm_active": swarm is not None,
        }

    # --- Chat endpoint ---

    @app.post("/chat")
    async def chat(req: ChatRequest):
        from nexus.llm.schemas import LLMRequest, Message

        memory.add_message(req.session_id, Message(role="user", content=req.message))
        messages = memory.get_messages(req.session_id)

        context = await memory.get_context_for_prompt(req.message)
        if context:
            augmented = list(messages)
            augmented.insert(-1, Message(role="system", content=context))
        else:
            augmented = messages

        response = await router.complete(LLMRequest(messages=augmented))
        memory.add_message(req.session_id, Message(role="assistant", content=response.content))

        return {"response": response.content, "session_id": req.session_id}

    # --- WebSocket streaming chat ---

    @app.websocket("/ws/chat")
    async def ws_chat(ws: WebSocket):
        await ws.accept()
        session_id = "ws"
        from nexus.llm.schemas import LLMRequest, Message

        # Send system prompt
        system_prompt = (
            "You are NEXUS, a hyper-intelligent AI assistant. "
            "Be helpful, precise, and creative."
        )
        memory.add_message(session_id, Message(role="system", content=system_prompt))

        try:
            while True:
                data = await ws.receive_json()
                user_msg = data.get("message", "")
                if not user_msg:
                    continue

                memory.add_message(session_id, Message(role="user", content=user_msg))
                messages = memory.get_messages(session_id)

                request = LLMRequest(messages=messages, stream=True)
                full = ""

                async for chunk in router.stream(request):
                    if chunk.is_final:
                        break
                    full += chunk.content
                    await ws.send_json({"type": "chunk", "content": chunk.content})

                memory.add_message(session_id, Message(role="assistant", content=full))
                await ws.send_json({"type": "done", "content": full})

        except WebSocketDisconnect:
            memory.clear_session(session_id)

    # --- Swarm goal execution ---

    @app.post("/swarm/execute")
    async def swarm_execute(req: GoalRequest):
        if not swarm:
            return {"error": "Swarm not initialized"}

        updates = []
        async for update in swarm.execute_goal(req.goal, req.context):
            updates.append({
                "type": update.update_type,
                "content": update.content,
                "task_id": update.task_id,
                "agent_id": update.agent_id,
                "is_final": update.is_final,
            })
        return {"goal": req.goal, "updates": updates}

    @app.get("/swarm/status")
    async def swarm_status():
        if not swarm:
            return {"error": "Swarm not initialized"}
        return {"status": swarm.status_summary()}

    # --- Skills ---

    @app.get("/skills")
    async def list_skills():
        if not skills:
            return {"skills": []}
        result = []
        for name in skills.list_skills():
            skill = skills.get(name)
            result.append({
                "name": name,
                "description": skill.manifest.description,
                "version": skill.manifest.version,
                "parameters": {
                    k: {"type": v.type, "description": v.description, "required": v.required}
                    for k, v in skill.manifest.parameters.items()
                },
            })
        return {"skills": result}

    @app.post("/skills/invoke")
    async def invoke_skill(req: SkillInvokeRequest):
        if not skills:
            return {"error": "Skills not initialized"}
        result = await skills.invoke(req.skill_name, req.params)
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    # --- Memory ---

    @app.get("/memory/stats")
    async def memory_stats():
        return await memory.stats()

    @app.post("/memory/consolidate")
    async def trigger_consolidation():
        created = await memory.consolidate_now()
        return {"knowledge_entries_created": created}

    # --- Web dashboard ---

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return DASHBOARD_HTML

    return app


DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NEXUS Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
    min-height: 100vh;
  }
  .header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 1.5rem 2rem;
    border-bottom: 1px solid #2a2a4a;
  }
  .header h1 {
    font-size: 1.8rem;
    background: linear-gradient(90deg, #00d2ff, #7b2ff7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 0.15em;
  }
  .header p { color: #888; font-size: 0.85rem; margin-top: 0.3rem; }
  .container { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1.5rem; }
  .card {
    background: #12121a;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 1.2rem;
  }
  .card h2 {
    font-size: 1rem;
    color: #7b2ff7;
    margin-bottom: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .chat-container { grid-column: 1 / -1; }
  #chat-messages {
    height: 350px;
    overflow-y: auto;
    padding: 0.5rem;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    margin-bottom: 0.8rem;
    background: #0a0a0f;
  }
  .msg { margin: 0.5rem 0; padding: 0.6rem 1rem; border-radius: 8px; max-width: 80%; }
  .msg.user { background: #1a1a3e; margin-left: auto; text-align: right; }
  .msg.assistant { background: #1e2a1e; }
  .msg.system { background: #2a1a1a; font-style: italic; font-size: 0.85rem; color: #aaa; }
  .input-row { display: flex; gap: 0.5rem; }
  .input-row input {
    flex: 1;
    padding: 0.7rem 1rem;
    background: #1a1a2e;
    border: 1px solid #3a3a5a;
    border-radius: 8px;
    color: #e0e0e0;
    font-size: 0.95rem;
  }
  .input-row input:focus { outline: none; border-color: #7b2ff7; }
  .btn {
    padding: 0.7rem 1.5rem;
    background: linear-gradient(135deg, #7b2ff7, #00d2ff);
    border: none;
    border-radius: 8px;
    color: white;
    cursor: pointer;
    font-weight: 600;
  }
  .btn:hover { opacity: 0.9; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .stat { display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid #1a1a2e; }
  .stat-label { color: #888; }
  .stat-value { color: #00d2ff; font-weight: 600; }
  .skill-item { padding: 0.5rem; border: 1px solid #2a2a4a; border-radius: 6px; margin: 0.3rem 0; }
  .skill-name { color: #7b2ff7; font-weight: 600; }
  .skill-desc { font-size: 0.85rem; color: #888; }
  @media (max-width: 768px) { .container { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<div class="header">
  <h1>N E X U S</h1>
  <p>Network of Evolving eXpert Unified Systems</p>
</div>

<div class="container">
  <div class="card chat-container">
    <h2>Chat</h2>
    <div id="chat-messages"></div>
    <div class="input-row">
      <input type="text" id="chat-input" placeholder="Type a message..." autocomplete="off">
      <button class="btn" id="send-btn" onclick="sendMessage()">Send</button>
    </div>
  </div>

  <div class="card">
    <h2>System Info</h2>
    <div id="system-info">Loading...</div>
  </div>

  <div class="card">
    <h2>Memory</h2>
    <div id="memory-stats">Loading...</div>
  </div>

  <div class="card">
    <h2>Skills</h2>
    <div id="skills-list">Loading...</div>
  </div>

  <div class="card">
    <h2>Swarm</h2>
    <div id="swarm-status">Loading...</div>
  </div>
</div>

<script>
  let ws = null;

  function connectWS() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/chat`);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'chunk') {
        appendOrUpdateAssistant(data.content);
      } else if (data.type === 'done') {
        finalizeAssistant();
        document.getElementById('send-btn').disabled = false;
      }
    };
    ws.onclose = () => setTimeout(connectWS, 2000);
  }

  let currentAssistant = null;

  function appendOrUpdateAssistant(chunk) {
    if (!currentAssistant) {
      currentAssistant = document.createElement('div');
      currentAssistant.className = 'msg assistant';
      currentAssistant.textContent = '';
      document.getElementById('chat-messages').appendChild(currentAssistant);
    }
    currentAssistant.textContent += chunk;
    const box = document.getElementById('chat-messages');
    box.scrollTop = box.scrollHeight;
  }

  function finalizeAssistant() { currentAssistant = null; }

  function addMessage(text, cls) {
    const div = document.createElement('div');
    div.className = 'msg ' + cls;
    div.textContent = text;
    document.getElementById('chat-messages').appendChild(div);
    const box = document.getElementById('chat-messages');
    box.scrollTop = box.scrollHeight;
  }

  function sendMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg || !ws || ws.readyState !== 1) return;
    addMessage(msg, 'user');
    ws.send(JSON.stringify({ message: msg }));
    input.value = '';
    document.getElementById('send-btn').disabled = true;
  }

  document.getElementById('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
  });

  async function loadInfo() {
    try {
      const r = await fetch('/info');
      const d = await r.json();
      document.getElementById('system-info').innerHTML =
        `<div class="stat"><span class="stat-label">Version</span><span class="stat-value">${d.version}</span></div>` +
        `<div class="stat"><span class="stat-label">Providers</span><span class="stat-value">${d.providers.join(', ')}</span></div>` +
        `<div class="stat"><span class="stat-label">Skills</span><span class="stat-value">${d.skills.length}</span></div>` +
        `<div class="stat"><span class="stat-label">Swarm</span><span class="stat-value">${d.swarm_active ? 'Active' : 'Inactive'}</span></div>`;
    } catch { document.getElementById('system-info').textContent = 'Error loading'; }
  }

  async function loadMemory() {
    try {
      const r = await fetch('/memory/stats');
      const d = await r.json();
      let html = '';
      for (const [k, v] of Object.entries(d)) {
        html += `<div class="stat"><span class="stat-label">${k.replace(/_/g, ' ')}</span><span class="stat-value">${v}</span></div>`;
      }
      document.getElementById('memory-stats').innerHTML = html || 'No data';
    } catch { document.getElementById('memory-stats').textContent = 'Error loading'; }
  }

  async function loadSkills() {
    try {
      const r = await fetch('/skills');
      const d = await r.json();
      if (!d.skills.length) { document.getElementById('skills-list').textContent = 'No skills'; return; }
      let html = '';
      for (const s of d.skills) {
        html += `<div class="skill-item"><span class="skill-name">${s.name}</span> <span class="skill-desc">${s.description}</span></div>`;
      }
      document.getElementById('skills-list').innerHTML = html;
    } catch { document.getElementById('skills-list').textContent = 'Error loading'; }
  }

  async function loadSwarm() {
    try {
      const r = await fetch('/swarm/status');
      const d = await r.json();
      document.getElementById('swarm-status').innerHTML =
        `<pre style="white-space:pre-wrap;color:#aaa;font-size:0.85rem">${d.status || d.error || 'Unknown'}</pre>`;
    } catch { document.getElementById('swarm-status').textContent = 'Error loading'; }
  }

  connectWS();
  loadInfo();
  loadMemory();
  loadSkills();
  loadSwarm();
  setInterval(() => { loadMemory(); loadSwarm(); }, 15000);
</script>

</body>
</html>
"""
