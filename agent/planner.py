"""
agent/planner.py
══════════════════════════════════════════════════════════════════════════════
AGENT STEP 1 — Slide Planner
══════════════════════════════════════════════════════════════════════════════

Responsibilities:
  1. Extract the main topic from user request for focused content
  2. Pick the best visual style for the topic
  3. Ask the LLM for a full JSON slide outline (with topic constraint)
  4. Parse + validate the JSON
  5. Return a clean list of slide dicts + the chosen style name

Topic Focus:
  All generated slides MUST be directly related to the main topic extracted
  from the user's request. This ensures cohesiveness across the presentation.
"""

import json
import re
from agent.llm_client import ask_llm

# ── Style keyword map ─────────────────────────────────────────────────────────
STYLE_KEYWORDS = {
    "dark":      ["tech", "ai", "cyber", "code", "software", "engineering",
                  "machine learning", "data science", "physics", "astronomy",
                  "space", "star", "quantum", "robot", "computing"],
    "minimal":   ["art", "history", "literature", "philosophy", "culture",
                  "museum", "ancient", "classical", "poetry", "architecture"],
    "gradient":  ["design", "startup", "creative", "branding", "marketing",
                  "innovation", "social media", "ux", "ui", "fashion"],
    "nature":    ["biology", "environment", "ecology", "plant", "animal",
                  "health", "sustainability", "climate", "ocean", "forest",
                  "wildlife", "nutrition", "fitness"],
    "corporate": ["business", "finance", "economics", "strategy", "management",
                  "leadership", "sales", "report", "company", "corporate",
                  "investment", "accounting", "law", "policy"],
}


def pick_style(user_request: str) -> str:
    """Choose the best visual style by matching keywords in the prompt."""
    lower = user_request.lower()
    scores = {style: 0 for style in STYLE_KEYWORDS}
    for style, keywords in STYLE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[style] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "corporate"

def _extract_topic(user_request: str) -> str:
    """Extract the main topic/keyword from the user prompt."""
    # Remove common words and get the core topic
    words = user_request.lower().split()
    # Filter out common stop words and very short words
    stop_words = {"a", "an", "the", "for", "about", "tell", "me", "explain", 
                  "on", "in", "of", "and", "or", "is", "are", "be", "create",
                  "make", "write", "generate", "build", "show", "display", "add",
                  "list", "give", "provide", "describe", "class", "grade", "school",
                  "presentation", "slide", "slides", "deck", "ppt", "5", "6"}
    
    topic_words = [w.strip('.,!?;:') for w in words 
                   if w.strip('.,!?;:') not in stop_words and len(w.strip('.,!?;:')) > 2]
    
    if topic_words:
        # Return first few meaningful words as topic
        return " ".join(topic_words[:5])
    return user_request[:60]

# ── Prompt template ───────────────────────────────────────────────────────────
PLAN_PROMPT = """You are a professional presentation planner creating a cohesive, focused presentation.

USER REQUEST:
"{user_request}"

MAIN TOPIC TO FOCUS ON:
"{main_topic}"

CRITICAL CONSTRAINT - ALL SLIDES MUST:
✓ Be directly related to the main topic: "{main_topic}"
✓ Build on each other in a logical sequence
✓ Use consistent terminology from the topic domain
✓ Avoid tangents or unrelated subjects
✓ Keep the audience and topic explicitly connected throughout

INSTRUCTIONS:
1. Determine how many slides the user wants (default 5 if not specified).
2. Slide 1 must be type "title" — introduce the main topic.
3. Slide 2+ must be type "content" — each focused on one aspect of the main topic.
4. The last slide must be type "closing" — summarize the main topic.
5. Each slide needs 3–5 bullet points that are COMPLETE SENTENCES (not keywords).
6. Make the content factual, educational, and explicitly tied to: "{main_topic}"
7. Tailor the depth to the audience mentioned (e.g. "6th grade" = simple language).

SLIDE PROGRESSION EXAMPLE FOR "{main_topic}":
  → Slide 1: What is {main_topic}? (Title)
  → Slide 2: Key concepts of {main_topic} (Content)
  → Slide 3: How {main_topic} works / Applications (Content)
  → Slide 4: Real-world examples of {main_topic} (Content)
  → Slide 5: Summary of {main_topic} (Closing)

Return ONLY a valid JSON array. No markdown, no explanation, no code fences.

Format:
[
  {{
    "slide_number": 1,
    "slide_title": "What is {main_topic}?",
    "slide_type": "title",
    "bullet_points": ["Sentence 1 about {main_topic}.", "Sentence 2.", "Sentence 3."]
  }},
  {{
    "slide_number": 2,
    "slide_title": "[Aspect of {main_topic}]",
    "slide_type": "content",
    "bullet_points": ["Sentence 1 explaining this aspect of {main_topic}.", "Sentence 2.", "Sentence 3."]
  }},
  ...
]

JSON array only:
"""


def plan_slides(user_request: str, log_callback=None) -> tuple[list[dict], str]:
    """
    Plan the slide outline and select a visual style.

    Parameters
    ----------
    user_request : str
        The user's natural language request
    log_callback : callable, optional
        Function to log progress messages

    Returns
    -------
    (slide_plan, style_name)
        List of slide dicts and the chosen visual style
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    # ── Extract main topic ─────────────────────────────────────────────────────
    main_topic = _extract_topic(user_request)
    log(f"📌 **Main topic extracted:** `{main_topic}`")

    # ── Pick style ────────────────────────────────────────────────────────────
    style = pick_style(user_request)
    log(f"🎨 **Visual style selected:** `{style}`")

    # ── Ask LLM for outline ───────────────────────────────────────────────────
    log("🧠 **Step 1: Planning slide outline...**")
    prompt   = PLAN_PROMPT.format(user_request=user_request, main_topic=main_topic)
    raw      = ask_llm(prompt, temperature=0.5)
    log(f"📋 LLM outline received ({len(raw)} chars)")

    plan = _parse_json(raw)
    if plan is None:
        log("⚠️  JSON parse failed — using fallback plan.")
        plan = _fallback_plan(user_request)

    plan = _sanitize(plan)
    log(f"✅ Plan ready: {len(plan)} slides  |  Style: {style}  |  Topic: {main_topic}")
    for s in plan:
        log(f"   Slide {s['slide_number']}: {s['slide_title']} [{s['slide_type']}]")

    return plan, style


# ── JSON parsing with three fallback strategies ───────────────────────────────

def _parse_json(text: str):
    # 1. Direct
    try:
        d = json.loads(text)
        if isinstance(d, list):
            return d
    except json.JSONDecodeError:
        pass
    # 2. Find first [...] block
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group())
            if isinstance(d, list):
                return d
        except json.JSONDecodeError:
            pass
    # 3. Strip markdown fences
    cleaned = re.sub(r'```(?:json)?', '', text).strip()
    try:
        d = json.loads(cleaned)
        if isinstance(d, list):
            return d
    except json.JSONDecodeError:
        pass
    return None


def _sanitize(plan: list) -> list:
    valid = {"title", "content", "closing"}
    out   = []
    for i, s in enumerate(plan):
        out.append({
            "slide_number":  s.get("slide_number", i + 1),
            "slide_title":   str(s.get("slide_title", f"Slide {i+1}"))[:80],
            "slide_type":    s.get("slide_type", "content")
                             if s.get("slide_type") in valid else "content",
            "bullet_points": [str(b)[:200] for b in s.get("bullet_points", [])[:5]]
                             or ["Content coming soon."]
        })
    if out:
        out[0]["slide_type"]  = "title"
        out[-1]["slide_type"] = "closing"
    return out


def _fallback_plan(user_request: str) -> list:
    """Fallback slide plan if LLM fails to generate one."""
    topic = _extract_topic(user_request)
    return [
        {"slide_number": 1, "slide_title": f"Introduction to {topic}", "slide_type": "title",
         "bullet_points": [f"Understanding {topic} and its importance.",
                           "Key concepts and core principles.",
                           "What you will learn in this presentation."]},
        {"slide_number": 2, "slide_title": f"Background: What is {topic}?", "slide_type": "content",
         "bullet_points": [f"Defining {topic} and key terminology.",
                           f"Historical context of {topic}.",
                           f"Why {topic} is important today."]},
        {"slide_number": 3, "slide_title": f"Core Aspects of {topic}", "slide_type": "content",
         "bullet_points": [f"Main principles and concepts within {topic}.",
                           f"How different elements of {topic} work together.",
                           f"Building blocks and foundational ideas."]},
        {"slide_number": 4, "slide_title": f"Practical Applications of {topic}", "slide_type": "content",
         "bullet_points": [f"Real-world examples of {topic} in action.",
                           f"How {topic} impacts science, society, or technology.",
                           f"Case studies and interesting discoveries."]},
        {"slide_number": 5, "slide_title": f"Summary: Key Takeaways on {topic}", "slide_type": "closing",
         "bullet_points": [f"Most important points about {topic}.",
                           f"Quick review of what {topic} means.",
                           "Thank you for learning about this topic!"]},
    ]
