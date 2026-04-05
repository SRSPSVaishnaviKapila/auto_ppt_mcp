# streamlit_app/app.py

import streamlit as st
import asyncio
import threading
import queue
import os
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.planner import plan_slides, pick_style
from agent.executor import execute_plan


# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Auto PPT Generator",
    page_icon="🎯",
    layout="centered"
)

# ─────────────────────────────────────────────
# 🎨 Colorful UI Styling
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* ════════════════════════════════════════════════════════════════════ */
    /* MODERN PREMIUM DESIGN */
    /* ════════════════════════════════════════════════════════════════════ */
    
    /* Root & Background */
    .stApp {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        min-height: 100vh;
    }
    
    /* Main Container */
    .block-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 3rem 2rem;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* TYPOGRAPHY */
    /* ════════════════════════════════════════════════════════════════════ */
    
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }
    
    h1 {
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h2 {
        font-size: 1.8rem !important;
        margin-top: 2rem !important;
        margin-bottom: 1.5rem !important;
    }
    
    h3 {
        font-size: 1.3rem !important;
        color: #e0e8f0 !important;
    }
    
    p, span {
        color: #c5cfe0 !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* FORM ELEMENTS */
    /* ════════════════════════════════════════════════════════════════════ */
    
    /* Labels */
    label {
        color: #e0e8f0 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Text Input */
    .stTextInput input {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #1a2332 !important;
        border: 2px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    }
    
    .stTextInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4) !important;
        transform: translateY(-2px);
    }
    
    .stTextInput input::placeholder {
        color: #8899aa !important;
    }
    
    /* Select Box */
    .stSelectbox {
        margin-bottom: 1rem !important;
    }
    
    .stSelectbox div[data-baseweb="select"] {
        background: rgba(255, 255, 255, 0.95) !important;
    }
    
    [data-baseweb="select"] input {
        color: #1a2332 !important;
    }
    
    [data-baseweb="select"] > div {
        border-radius: 12px !important;
        border: 2px solid rgba(102, 126, 234, 0.3) !important;
        background: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* Checkbox */
    .stCheckbox {
        padding: 0.5rem 0;
    }
    
    .stCheckbox label {
        color: #e0e8f0 !important;
        font-weight: 500 !important;
        cursor: pointer;
        transition: color 0.2s ease;
    }
    
    .stCheckbox label:hover {
        color: #667eea !important;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* BUTTONS */
    /* ════════════════════════════════════════════════════════════════════ */
    
    /* Primary Button (Generate) */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(102, 126, 234, 0.5) !important;
    }
    
    .stButton > button:active {
        transform: translateY(-1px);
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 8px 20px rgba(67, 206, 162, 0.3) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(67, 206, 162, 0.5) !important;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* CARDS & CONTAINERS */
    /* ════════════════════════════════════════════════════════════════════ */
    
    /* Metric Cards */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.08) !important;
        padding: 1.5rem !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="metric-container"]:hover {
        background: rgba(255, 255, 255, 0.12) !important;
        border-color: rgba(102, 126, 234, 0.5) !important;
        transform: translateY(-2px);
    }
    
    /* Expander */
    .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
    }
    
    .stExpander {
        background: rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* CODE & LOGS */
    /* ════════════════════════════════════════════════════════════════════ */
    
    pre {
        background: rgba(0, 0, 0, 0.4) !important;
        color: #00ffcc !important;
        padding: 16px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(0, 255, 204, 0.2) !important;
        font-size: 0.85rem !important;
        overflow-x: auto !important;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    code {
        color: #00ffcc !important;
        font-family: 'Courier New', monospace !important;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* COLUMNS */
    /* ════════════════════════════════════════════════════════════════════ */
    
    .stColumn {
        transition: all 0.3s ease;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* SUCCESS/ERROR MESSAGES */
    /* ════════════════════════════════════════════════════════════════════ */
    
    .stSuccess {
        background: rgba(67, 206, 162, 0.15) !important;
        border: 1px solid rgba(67, 206, 162, 0.5) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }
    
    .stError {
        background: rgba(255, 107, 107, 0.15) !important;
        border: 1px solid rgba(255, 107, 107, 0.5) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }
    
    .stWarning {
        background: rgba(255, 193, 7, 0.15) !important;
        border: 1px solid rgba(255, 193, 7, 0.5) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }
    
    .stInfo {
        background: rgba(102, 126, 234, 0.15) !important;
        border: 1px solid rgba(102, 126, 234, 0.5) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* CUSTOM ANIMATIONS */
    /* ════════════════════════════════════════════════════════════════════ */
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3); }
        50% { box-shadow: 0 8px 30px rgba(102, 126, 234, 0.5); }
    }
    
    .stApp {
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* ════════════════════════════════════════════════════════════════════ */
    /* SCROLLBAR */
    /* ════════════════════════════════════════════════════════════════════ */
    
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(102, 126, 234, 0.5);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(102, 126, 234, 0.8);
    }
    
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────
for key, default in {
    "slide_plan": None,
    "output_path": None,
    "logs": [],
    "running": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.title("🎯 Auto PPT Generator")
st.caption("Generate beautiful PowerPoint presentations using AI")


# ─────────────────────────────────────────────
# Inputs
# ─────────────────────────────────────────────
prompt = st.text_input(
    "Enter your topic",
    placeholder="e.g. Create a 5-slide presentation on AI for beginners"
)

col1, col2 = st.columns(2)

with col1:
    use_search = st.checkbox("Use Wikipedia", value=True)

with col2:
    style = st.selectbox(
        "Style",
        ["auto", "corporate", "dark", "minimal", "gradient", "nature"]
    )

generate = st.button("🚀 Generate Presentation", use_container_width=True)


# ─────────────────────────────────────────────
# Agent Runner
# ─────────────────────────────────────────────
def run_agent(prompt, use_search, style, q):

    def log(msg):
        q.put(("log", msg))

    try:
        plan, auto_style = plan_slides(prompt, log_callback=log)
        q.put(("plan", plan))

        final_style = auto_style if style == "auto" else style
        log(f"Using style: {final_style}")

        safe = re.sub(r'[^a-zA-Z0-9_]', '_', prompt[:30])
        fname = f"{safe}.pptx"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        path = loop.run_until_complete(
            execute_plan(
                slide_plan=plan,
                style=final_style,
                user_request=prompt,
                output_filename=fname,
                use_search=use_search,
                log_callback=log
            )
        )

        loop.close()
        q.put(("done", path))

    except Exception as e:
        q.put(("error", str(e)))


# ─────────────────────────────────────────────
# Run Agent
# ─────────────────────────────────────────────
if generate and prompt.strip():

    st.session_state.running = True
    st.session_state.logs = []
    st.session_state.slide_plan = None
    st.session_state.output_path = None

    q = queue.Queue()

    thread = threading.Thread(
        target=run_agent,
        args=(prompt, use_search, style, q),
        daemon=True
    )
    thread.start()

    st.subheader("⚙️ Generating...")

    log_box = st.empty()
    plan_box = st.empty()

    logs = []

    while thread.is_alive() or not q.empty():
        try:
            mtype, data = q.get(timeout=0.2)

            if mtype == "log":
                logs.append(data)
                log_box.text("\n".join(logs[-15:]))

            elif mtype == "plan":
                st.session_state.slide_plan = data
                plan_box.json(data)

            elif mtype == "done":
                st.session_state.output_path = data
                st.session_state.running = False

            elif mtype == "error":
                st.error(data)
                st.session_state.running = False

        except queue.Empty:
            pass

    thread.join()
    st.rerun()


# ─────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────
if st.session_state.output_path and os.path.exists(st.session_state.output_path):

    st.success("✅ Presentation Ready!")

    with open(st.session_state.output_path, "rb") as f:
        st.download_button(
            "⬇ Download PPT",
            data=f,
            file_name=os.path.basename(st.session_state.output_path)
        )

    if st.session_state.slide_plan:
        with st.expander("📋 Slide Summary"):
            for slide in st.session_state.slide_plan:
                st.write(f"**Slide {slide['slide_number']}** - {slide['slide_title']}")
                for b in slide["bullet_points"]:
                    st.write(f"- {b}")