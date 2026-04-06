#  Reflection Document — Auto-PPT Agent

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

### **a) Content Generation Issues**

The agent initially produced repetitive and generic bullet points. The content lacked depth and variation because it relied on predefined templates rather than dynamic generation. When external APIs such as Hugging Face were introduced, additional issues arose due to invalid responses and token-related errors, which disrupted the content generation process.

---

### **b) Image Generation Problems**

The agent faced difficulties in incorporating images into the presentation slides. In many cases, image URLs were either invalid or unavailable. Additionally, the PowerPoint generation logic did not correctly handle image insertion, resulting in slides without proper visual elements.

---

### **c) MCP Server Connection Errors**

There were multiple failures in establishing a connection between the agent and the MCP server. Common errors included incorrect file paths (such as the system being unable to locate `ppt_server.py`) and server startup failures. These issues were primarily caused by improper relative path handling and differences in execution context when running the application through Streamlit.

---

### **d) Token Validation Issues**

While integrating external services, the agent encountered problems related to API key configuration. Missing or invalid tokens, along with incorrect environment variable setup, caused failures in accessing external APIs. This led to interruptions in generating slide content.

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

Here is a clean, formal version suitable for your report:

---

### **a) Separation of Concerns**

MCP enforces a clear separation between the agent and the execution layer. The agent is responsible for decision-making, while the MCP server handles tool execution. This modular design eliminates the need to embed all logic within a single script.

---

### **b) Tool-Based Architecture**

The system is built around reusable tools such as `create_presentation`, `add_slide`, and `save_presentation`. The agent invokes these tools dynamically instead of relying on hardcoded procedures for creating slides.

---

### **c) Dynamic Execution**

The agent follows an agentic workflow where it plans and executes tasks step by step. It determines when to create slides, what content to include, and when to save the presentation. This replaces static, hardcoded workflows with flexible and adaptive behavior.

---

### **d) Reusability and Scalability**

MCP tools are independent and reusable across different agents or applications. This reduces duplication of code and allows the system to scale efficiently without rewriting core functionality.

---

### **e) Improved Error Handling**

The modular structure enables better handling of failures. If a tool fails, the agent can implement fallback strategies such as generating default content instead of terminating execution.

---

## **Conclusion**

The initial version of the agent faced challenges related to content generation, image handling, MCP connectivity, and API integration. By adopting the MCP architecture, the system evolved into a modular and scalable solution. This approach eliminated hardcoded logic, improved flexibility, and enhanced the robustness of the Auto-PPT agent.


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
