# 📝 Reflection Document — Auto-PPT Agent

## Assignment Questions

---

### Q1: Where did your agent fail its first attempt?

**Problem 1 — JSON Parsing**
The LLM (Mistral 7B) frequently returned its JSON slide plan wrapped in
markdown code fences (` ```json ... ``` `). The first version of `planner.py`
used `json.loads()` directly and crashed on every single response.

**Fix:** The `_parse_json_from_response()` function now tries three strategies:
1. Direct `json.loads()`
2. Regex to find the `[...]` block
3. Strip markdown fences and retry

---

**Problem 2 — MCP Server Cold Start**
When `executor.py` launched the MCP server subprocess the first time,
`pptx_server.py` took ~1-2 seconds to start. The client was sending
`initialize()` before the server was ready, causing a connection refused error.

**Fix:** The `mcp` SDK's `stdio_client` context manager handles the handshake
protocol correctly. Wrapping both sessions in `async with` ensures proper
initialization order.

---

**Problem 3 — Bullet Points Too Short**
The LLM initially generated single-word bullets like `"Nebulae"` or `"Gravity"`
because the prompt said "bullet points" without specifying length.

**Fix:** The prompt template now says:
> "Bullet points should be COMPLETE sentences (not just keywords)."

---

**Problem 4 — Missing Fallback**
When Wikipedia returned a 404 (topic not found), the executor raised an
unhandled `KeyError` when trying to read `search_data["content"]`.

**Fix:** `_parse_tool_result()` always returns a default empty `{}`, and
`.get("content", "")` safely returns an empty string which triggers the
"use LLM knowledge" path.

---

### Q2: How did MCP prevent you from writing hardcoded scripts?

**Separation of concerns via protocol:**

In a traditional script, you'd write something like this:
```python
# Hardcoded — tightly coupled
from pptx import Presentation
prs = Presentation()
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "My Title"
# ... 100 more lines
```

With MCP, the agent's "brain" (`executor.py`) has ZERO imports from
`python-pptx`. It only sends JSON tool-call messages:
```python
await pptx_session.call_tool("add_slide", {
    "slide_title": "Birth of a Star",
    "bullet_points": ["Stars form in nebulae", ...],
    "slide_type": "content"
})
```

**Why this matters:**
- You could replace `pptx_server.py` with one that calls the Google Slides API
  and the `executor.py` would not need a single line changed.
- You could add a `database_server.py` MCP server to log all presentations to
  PostgreSQL without touching the agent.
- The agent can be tested independently by mocking the MCP tool responses.

**The planning step was forced by the architecture:**
Because MCP tools are asynchronous calls with latency, the agent *must* plan
the full slide structure upfront. Doing 10 back-and-forth LLM calls to decide
"what goes on slide 3?" mid-loop would be too slow and incoherent. The two-step
plan-then-execute structure emerges naturally from the MCP design.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT (MCP Client)                       │
│                    streamlit_app/app.py                         │
│  User types prompt → runs agent → shows logs → download button  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT BRAIN                                  │
│  ┌──────────────────────┐   ┌──────────────────────────────┐   │
│  │  planner.py          │   │  executor.py                 │   │
│  │                      │   │                              │   │
│  │  Prompt → LLM →      │   │  FOR each slide:             │   │
│  │  JSON slide plan      │──▶│    call search MCP           │   │
│  │                      │   │    call pptx MCP             │   │
│  └──────────────────────┘   │  CALL save_presentation      │   │
│                              └──────────────────────────────┘   │
└───────────────┬───────────────────────────┬─────────────────────┘
                │  MCP Protocol             │  MCP Protocol
                ▼                           ▼
┌───────────────────────┐     ┌────────────────────────────┐
│  MCP SERVER 1         │     │  MCP SERVER 2              │
│  pptx_server.py       │     │  search_server.py          │
│                       │     │                            │
│  Tools:               │     │  Tools:                    │
│  • create_presentation│     │  • search_web (Wikipedia)  │
│  • add_slide          │     │  • fetch_image (Pexels)    │
│  • save_presentation  │     │                            │
└───────────────────────┘     └────────────────────────────┘
          │                                │
          ▼                                ▼
   outputs/*.pptx              Wikipedia REST API
                                   Pexels API
```
