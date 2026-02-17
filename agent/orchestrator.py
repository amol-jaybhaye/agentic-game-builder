import json
import os
import re
from typing import List, Tuple
from agent.llm import chat_text
from agent.prompts import SYSTEM, CLARIFY, PLAN, BUILD

MODEL = os.environ.get("OPENAI_MODEL", "llama-3.1-8b-instant")

def _ask_user(question: str) -> str:
    print("\n" + question.strip() + "\n> ", end="", flush=True)
    return input().strip()

def _format_qa(qa: List[Tuple[str, str]]) -> str:
    if not qa:
        return "(none)"
    out = []
    for i, (q, a) in enumerate(qa, 1):
        out.append(f"{i}. Q: {q}\n   A: {a}")
    return "\n".join(out)

def _parse_plan_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))

def _parse_files(payload: str) -> dict:
    pattern = r"===FILE:(.+?)===\n(.*?)\n===END==="
    matches = re.findall(pattern, payload, re.DOTALL)
    files = {name.strip(): content.rstrip() + "\n" for name, content in matches}
    return files

def _sanity_check_files(files: dict):
    required = {"index.html", "style.css", "game.js"}
    missing = required - set(files.keys())
    if missing:
        raise ValueError(f"Missing required files: {sorted(missing)}. Parsed keys: {sorted(files.keys())}")
    if "style.css" not in files["index.html"] or "game.js" not in files["index.html"]:
        raise ValueError("index.html must reference style.css and game.js")

def run_agent(initial_idea: str, output_dir: str):
    print("Agentic Game-Builder AI")
    qa: List[Tuple[str, str]] = []

    # ---- Clarify ----
    clarify_prompt = CLARIFY.format(idea=initial_idea, qa=_format_qa(qa))
    resp = chat_text(MODEL, [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": clarify_prompt}
    ], 0.2).strip()

    if resp != "NO_MORE_QUESTIONS":
        # If model outputs an intro paragraph + questions, that's fine; you answer once.
        lines = [l.strip() for l in resp.split("\n") if l.strip()]
        questions = [l for l in lines if "?" in l][-5:] 
        for q in questions:
            a = _ask_user(q)
            qa.append((q, a))

    # ---- Plan ----
    plan_prompt = PLAN.format(idea=initial_idea, qa=_format_qa(qa))
    plan_text = chat_text(MODEL, [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": plan_prompt}
    ], 0.1)

    plan = _parse_plan_json(plan_text)

    # Force plan file keys we actually need (your plan currently uses script.js etc.)
    plan.setdefault("files", {})
    plan["files"]["index.html"] = "must generate"
    plan["files"]["style.css"] = "must generate"
    plan["files"]["game.js"] = "must generate"

    plan_json = json.dumps(plan, indent=2)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "plan.json"), "w", encoding="utf-8") as f:
        f.write(plan_json + "\n")

    # ---- Build ----
    build_prompt = BUILD.format(plan_json=plan_json)
    build_text = chat_text(MODEL, [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": build_prompt}
    ], 0.2)

    files = _parse_files(build_text)

    # If missing, retry once with a “hard” instruction.
    try:
        _sanity_check_files(files)
    except Exception as e:
        repair_prompt = (
            build_prompt
            + "\n\nIMPORTANT: Your last output was invalid.\n"
            + f"ERROR: {str(e)}\n"
            + "Regenerate ONLY in the exact required format with THREE blocks for "
              "index.html, style.css, game.js. No extra text.\n"
        )
        build_text = chat_text(MODEL, [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": repair_prompt}
        ], 0.1)
        files = _parse_files(build_text)
        _sanity_check_files(files)

    # Write files
    for name, content in files.items():
        with open(os.path.join(output_dir, name), "w", encoding="utf-8") as f:
            f.write(content)

    print("Done. Open index.html in browser.")
