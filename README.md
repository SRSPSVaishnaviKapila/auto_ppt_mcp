# 🤖 Auto-PPT Agent

A fully agentic pipeline that takes a single sentence prompt and outputs a `.pptx` file —
powered by HuggingFace LLM, MCP servers, and a Streamlit UI.

---

## 📁 Project Structure

```
auto_ppt_agent/
│
├── .env                          ← API keys go here
├── README.md                     ← You are here
├── requirements.txt              ← All Python dependencies
│
├── mcp_servers/                  ← 🔧 MCP Tool Servers (the "hands" of the agent)
│   ├── pptx_server.py            ← MCP Server 1: Creates & writes PowerPoint files
│   └── search_server.py          ← MCP Server 2: Searches the web for content
│
├── agent/                        ← 🧠 Agent Brain (the "mind" of the system)
│   ├── llm_client.py             ← Connects to HuggingFace LLM
│   ├── planner.py                ← Step 1: Plans the slide outline
│   └── executor.py               ← Step 2: Executes slide-by-slide using MCP tools
│
├── streamlit_app/                ← 🖥️ Streamlit UI (the "face" of the system)
│   └── app.py                    ← Main Streamlit interface
│
└── outputs/                      ← 📂 Generated .pptx files are saved here
```

---

## 🚀 How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up your `.env` file
```
HUGGINGFACEHUB_API_TOKEN="your_huggingface_token_here"
PEXELS_API_KEY="your_pexels_key_here"
```

### 3. Start the app
```bash
streamlit run streamlit_app/app.py
```

---

## 🔄 How It Works (The Agentic Loop)

```
User Prompt
    │
    ▼
[PLANNER] ──→ LLM generates a JSON outline (slide titles + bullet points)
    │
    ▼
[EXECUTOR LOOP]
    ├── For each slide in outline:
    │       ├── Call MCP Tool: search_web (optional, fetches real data)
    │       ├── Call MCP Tool: add_slide (writes title + bullets to PPT)
    │       └── Repeat...
    │
    ▼
[SAVE] ──→ Call MCP Tool: save_presentation → outputs/my_presentation.pptx
    │
    ▼
Streamlit shows download button ✅
```

---

##  MCP Servers TOOLS

| Server | Tools It Provides | What It Does |
|--------|------------------|--------------|
| `pptx_server.py` | `create_presentation`, `add_slide`, `save_presentation` | Manages the PowerPoint file |
| `search_server.py` | `search_web` | Fetches real content using Pexels API |

---


## SCREEN RECORDING

https://github.com/user-attachments/assets/bd959186-d28b-4bee-841b-7c83c7628089


https://github.com/user-attachments/assets/4f81696c-a912-4c47-af95-17c0dd76c925

## 💡 Key Concepts

- **MCP (Model Context Protocol)**: A standard way for an LLM agent to call external tools.
  Instead of hardcoding the logic, the agent *decides* which tool to call.
- **Agentic Loop**: The agent plans first, then executes one slide at a time.
- **Graceful Fallback**: If search fails, the LLM generates content from its own knowledge.
