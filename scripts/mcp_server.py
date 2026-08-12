#!/usr/bin/env python3
"""Local MCP bridge for the sales-chat-quality skill.

The server exposes deterministic browser collection and timestamp scoring. Semantic
quality remains an LLM task and is returned as a prompt/evidence bundle for Codex.
"""
import json
import subprocess
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent
COLLECTOR = ROOT / "collect_chat.mjs"
SCORER = ROOT / "score_chats.py"
mcp = FastMCP("sales-chat-quality")

@mcp.tool()
def collect_sales_chats(cdp_url: str = "http://127.0.0.1:9222", output_dir: str = "", max_conversations: int = 20, max_pages: int = 1) -> str:
    """Collect read-only 售前详情 dialogs and screenshots from a logged-in Chrome CDP session."""
    destination = Path(output_dir or (Path.home() / "Desktop" / "售前聊天质检"))
    command = ["node", str(COLLECTOR), "--cdp-url", cdp_url, "--output", str(destination), "--max-conversations", str(max_conversations), "--max-pages", str(max_pages)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        return json.dumps({"ok": False, "error": result.stderr.strip() or result.stdout.strip(), "returncode": result.returncode}, ensure_ascii=False)
    return json.dumps({"ok": True, "output_dir": str(destination), "conversations_json": str(destination / "conversations.json"), "log": result.stdout.strip()}, ensure_ascii=False)

@mcp.tool()
def score_sales_chats(input_json: str, slow_threshold_seconds: int = 10) -> str:
    """Compute user-to-agent response seconds; >10 seconds is slow by default."""
    source = Path(input_json).expanduser().resolve()
    output = source.with_name("scored_conversations.json")
    command = [sys.executable, str(SCORER), str(source), "--output", str(output), "--slow-threshold", str(slow_threshold_seconds)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        return json.dumps({"ok": False, "error": result.stderr.strip() or result.stdout.strip(), "returncode": result.returncode}, ensure_ascii=False)
    data = json.loads(output.read_text(encoding="utf-8"))
    pairs = [m for c in data.get("conversations", []) for m in c.get("messages", []) if "response_seconds" in m]
    slow = sum(1 for m in pairs if m.get("response_band") == "回复慢")
    return json.dumps({"ok": True, "scored_json": str(output), "evaluation_prompt": str(output.with_name("evaluation_prompt.txt")), "response_pairs": len(pairs), "slow_pairs": slow, "slow_threshold_seconds": slow_threshold_seconds}, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run(transport="stdio")
