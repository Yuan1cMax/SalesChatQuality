#!/usr/bin/env python3
"""Compute deterministic response-latency baselines and build an AI evaluation prompt."""
import argparse
import json
from datetime import datetime
from pathlib import Path

TS = "%Y-%m-%d %H:%M:%S"

def parse_ts(value: object) -> datetime | None:
    try:
        return datetime.strptime(value, TS)
    except (TypeError, ValueError):
        return None

def score(messages: list[dict], slow_threshold: int) -> tuple[list[dict], list[int]]:
    if slow_threshold < 0:
        raise ValueError("slow_threshold must be non-negative")

    enriched: list[dict] = []
    latencies: list[int] = []
    last_buyer: datetime | None = None
    for msg in messages:
        item = dict(msg)
        current = parse_ts(msg.get("timestamp"))
        if msg.get("role") == "buyer":
            last_buyer = current
        elif msg.get("role") == "agent" and last_buyer and current:
            seconds = int((current - last_buyer).total_seconds())
            if seconds >= 0:
                item["response_seconds"] = seconds
                item["response_band"] = "回复慢" if seconds > slow_threshold else "正常"
                latencies.append(seconds)
            else:
                item["latency_error"] = "agent timestamp precedes buyer timestamp"
            last_buyer = None
        enriched.append(item)
    return enriched, latencies


def score_dataset(data: dict, slow_threshold: int) -> dict:
    result = dict(data)
    conversations = []
    for conversation in data.get("conversations", []):
        scored_conversation = dict(conversation)
        scored_conversation["messages"], latencies = score(
            conversation.get("messages", []), slow_threshold
        )
        scored_conversation["slow_threshold_seconds"] = slow_threshold
        scored_conversation["latency_summary"] = {
            "count": len(latencies),
            "average_seconds": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "max_seconds": max(latencies) if latencies else None,
        }
        conversations.append(scored_conversation)
    result["conversations"] = conversations
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--slow-threshold", type=int, default=10, help="超过该秒数标记为回复慢，默认 10")
    args = ap.parse_args()
    data = score_dataset(
        json.loads(args.input.read_text(encoding="utf-8")), args.slow_threshold
    )
    out = args.output or args.input.with_name("scored_conversations.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt = out.with_name("evaluation_prompt.txt")
    prompt.write_text("""你是客服质检员。请依据 scored_conversations.json 及每个 conversation-*.png 截图逐条评价。\n\n对每个会话输出：客服回复原文、上一条用户消息、response_seconds、响应速度结论；并检查需求理解、信息准确、价格/费用说明、下一步引导、语气与合规、是否遗漏问题。每项给出通过/不通过/无法判断，引用消息序号和原句，最后给出总评与一条改进建议。不要凭空补全截图外的信息。""", encoding="utf-8")
    print(f"写入 {out}\n写入 {prompt}")

if __name__ == "__main__":
    main()
