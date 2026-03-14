# 🍔 SnackStack — Layered Intelligence for Food

A **voice-enabled multi-agent food delivery assistant** built with **LangGraph**.

Accepts text or voice input, routes queries through an orchestrator to specialist agents, and responds with text or synthesised speech.

---

## Quick Start

```bash
cd snackstack

# 1. Set your OpenAI API key (pick one)
cp .env.example .env               # then paste your key in .env
# OR if it's already in your system environment, skip this step

# 2. Install everything
uv sync

# 3. Run
uv run snackstack
```

That's it. You should see:

```
SnackStack — Text mode
Type a query and press Enter. Commands: reset | quit

You > hi
SnackStack: Hello! Welcome to SnackStack. What can I help you find today?

You > show me vegan options
SnackStack: Here are our vegan dishes...

You > where is my order?
Agent needs info: Could you please provide your Order ID, Tracking ID, or Email?
You > ORD-203
SnackStack: Your Classic Cheeseburger (ORD-203) is currently being prepared...
```

---

## Prerequisites

**Python ≥ 3.11** and **uv** (recommended) or **pip**.

Install uv if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # macOS / Linux
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
```

---

## Installation

### Option A: uv ⚡ (recommended)

```bash
cd snackstack
uv sync                        # creates .venv, resolves deps, installs the package
uv sync --extra voice          # required for voice mode (mic recording + audio playback)
```

### Option B: pip

```bash
cd snackstack
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows (PowerShell)

pip install -e .
pip install -e ".[voice]"      # required for voice mode (sounddevice + soundfile)
```

---

## Running

With **uv** you don't need to activate the venv — `uv run` handles it:

```bash
uv run snackstack                            # text mode (default)
uv run snackstack --voice-out                # text input → voice output
uv run snackstack --voice                    # full voice (mic → speaker)
uv run snackstack --voice-out --tts-voice shimmer   # pick a TTS voice
```

Responses in voice modes are optimised for speech — no markdown formatting, bullet points, or numbered lists.

If you activated the venv (or used pip), you can run directly:

```bash
snackstack                                   # text mode
snackstack --voice-out                       # text input → voice output
snackstack --voice                           # full voice
```


Available TTS voices: `alloy` · `echo` · `fable` · `onyx` · `nova` · `shimmer`

### In-Session Commands

| Command | Action                     |
|---------|----------------------------|
| `reset` | Start a fresh conversation |
| `quit`  | Exit the assistant         |

---

## Architecture

```
Voice / Text Input
        │
        ▼
  ┌─────────────┐
  │ Orchestrator │  ← Structured-output routing (Pydantic schema)
  └──────┬──────┘
         │  Send() — parallel dispatch
    ┌────┴─────┐
    ▼          ▼
┌────────┐ ┌────────┐
│  Menu  │ │ Order  │  ← Each runs its own tool-calling loop
│ Agent  │ │ Agent  │
└───┬────┘ └───┬────┘
    │          │
    ▼          ▼
  ┌──────────────┐
  │ Synthesizer  │  ← Merges responses into one reply
  └──────┬───────┘
         │
         ▼
  Voice / Text Output
```

---

## Project Structure

```
snackstack/
├── snackstack/
│   ├── __init__.py
│   ├── main.py              # CLI entry point (text / voice modes)
│   ├── config.py            # LLM, embeddings, OpenAI client
│   ├── state.py             # Shared StackState definition
│   ├── graph.py             # StateGraph builder & compiler
│   ├── logger.py            # Centralized logging
│   │
│   ├── data/
│   │   ├── menu.py          # Menu catalog (8 dishes)
│   │   └── orders.py        # Order database + delivery policies
│   │
│   ├── tools/
│   │   ├── rag.py           # ChromaDB vector store builder
│   │   ├── menu_tools.py    # search_menu_catalog (RAG)
│   │   └── order_tools.py   # get_order_status
│   │
│   ├── agents/
│   │   ├── prompts.py       # System prompts for all nodes
│   │   ├── orchestrator.py  # Routes queries → agent(s)
│   │   ├── menu_agent.py    # Menu discovery agent
│   │   ├── order_agent.py   # Order support agent (with HITL)
│   │   └── synthesizer.py   # Merges multi-agent responses
│   │
│   └── voice/
│       ├── recorder.py      # Mic → Whisper STT
│       └── speaker.py       # Text → OpenAI TTS
│
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## Example Queries

| Query | Routed To |
|-------|-----------|
| "hi" / "hello" / "thanks" | Menu Agent (handles greetings) |
| "Show me vegan dishes" | Menu Agent |
| "What Indian food do you have under 300?" | Menu Agent |
| "anything works" (after asking about non-veg) | Menu Agent (uses conversation context) |
| "Where is my order ORD-201?" | Order Agent |
| "Track order ORD-203" | Order Agent |
| "Suggest a pizza and also check order ORD-202" | Both agents (parallel) |

---

## Human-in-the-Loop (HITL)

The **Order Agent** uses LangGraph's `interrupt()` to pause execution when the user query doesn't contain a recognizable identifier:

| Key Type | Pattern | Example |
|----------|---------|---------|
| Order ID | `ORD-XXX` | `ORD-201` |
| Tracking ID | `SSXXXTRKX` | `SS201TRK` |
| Email | `user@domain.com` | `priya@example.com` |

**Without identifier** — graph pauses and asks:

```
You > where is my order?

Agent needs info: I'd be happy to help with your order! Could you provide...
You > ORD-203

SnackStack: Your Classic Cheeseburger (ORD-203) is currently being prepared...
```

**With identifier** — runs straight through:

```
You > track order ORD-201

SnackStack: Your Butter Chicken order (ORD-201) is out for delivery...
```

In **voice mode** (`--voice`), HITL prompts are spoken aloud via TTS and the user's response is captured from the microphone.

---

## Key Concepts

| Concept | Where |
|---------|-------|
| **LangGraph StateGraph** with parallel dispatch via `Send()` | `graph.py`, `orchestrator.py` |
| **RAG** — ChromaDB semantic search over menu items | `tools/rag.py`, `tools/menu_tools.py` |
| **Structured output** — Pydantic schema for routing | `orchestrator.py` |
| **Self-contained tool loops** — agents run tools internally | `menu_agent.py`, `order_agent.py` |
| **Human-in-the-Loop** — `interrupt()` + `Command(resume=)` (voice-aware) | `order_agent.py`, `main.py` |
| **Multi-turn memory** — `MemorySaver` + conversation context passed to orchestrator & agents | `graph.py`, `orchestrator.py`, `menu_agent.py` |
| **Voice I/O** — Whisper STT + OpenAI TTS, playback via `sounddevice` | `voice/recorder.py`, `voice/speaker.py` |

---

## Extending

**Add a new tool** — create a file in `snackstack/tools/`, define your `@tool` function, add it to the agent's `_tools_list`.

**Add a new agent** — create a file in `snackstack/agents/`, follow the pattern in `menu_agent.py`, register it in `agents/__init__.py` and `graph.py`, and update the orchestrator prompt + Pydantic schema to include the new route.

**Swap the LLM** — edit `snackstack/config.py`. Any LangChain-compatible chat model works.