"""
agent/llm_client.py
══════════════════════════════════════════════════════════════════════════════
HuggingFace LLM Client
══════════════════════════════════════════════════════════════════════════════

This module wraps the HuggingFace Inference API so the rest of the agent
can call `ask_llm(prompt)` and get back a plain string.

Model choice:
  We use "mistralai/Mistral-7B-Instruct-v0.2" — a powerful open-source
  instruction-following model that is free on HuggingFace's Inference API.

  You can swap the model name below for any HuggingFace-hosted model.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")

# ── Model configuration ───────────────────────────────────────────────────────
# Mistral 7B works well for structured JSON generation tasks.
# Alternative models you could use:
#   "HuggingFaceH4/zephyr-7b-beta"
#   "google/flan-t5-xxl"
#   "tiiuae/falcon-7b-instruct"

MODEL_ID  = "mistralai/Mistral-7B-Instruct-v0.2"
API_URL   = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
MAX_TOKENS = 2048


def ask_llm(prompt: str, temperature: float = 0.7) -> str:
    """
    Send a prompt to the HuggingFace Inference API and return the response text.

    Parameters
    ----------
    prompt      : The full prompt string (system + user combined for HF models)
    temperature : Creativity level. 0.0 = deterministic, 1.0 = very creative.

    Returns
    -------
    str : The model's response text, or an error message string.
    """
    if not HF_TOKEN:
        raise ValueError(
            "HUGGINGFACEHUB_API_TOKEN is not set. "
            "Please add it to your .env file."
        )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type":  "application/json",
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens":    MAX_TOKENS,
            "temperature":       temperature,
            "return_full_text":  False,   # Only return the generated part
            "do_sample":         True,
        }
    }

    try:
        response = requests.post(API_URL, headers=headers,
                                 json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        # HF returns a list; the generated text is in result[0]["generated_text"]
        if isinstance(result, list) and result:
            return result[0].get("generated_text", "").strip()
        else:
            return str(result)

    except requests.exceptions.Timeout:
        # The model might be loading ("cold start") — return a helpful message
        return "ERROR: HuggingFace model timed out. The model may be loading. Try again in 30 seconds."

    except requests.exceptions.HTTPError as e:
        if response.status_code == 503:
            return "ERROR: Model is currently loading on HuggingFace. Please wait ~30s and retry."
        return f"ERROR: HTTP {response.status_code} — {e}"

    except Exception as e:
        return f"ERROR: {str(e)}"
