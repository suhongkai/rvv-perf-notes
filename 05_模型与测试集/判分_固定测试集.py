#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""固定测试集判分器（Qwen3.5 on K1 / llama-server）

用法：
    python3 判分_固定测试集.py --endpoint http://127.0.0.1:8097 \
        --testset 工业监控固定测试集_v1.json --rounds 5 --out 判分结果.json

协议（与测试集 JSON 里的 protocol 一致）：
  * 走 /v1/chat/completions（带 Qwen chat 模板），temperature=0，max_tokens=512；
  * 每题独立提问，不携带上一题历史；同一题在 N 轮里独立执行，用于看多轮的稳定性；
  * 判分：每题的 must_contain 是"关键词组"的列表，命中组数 / 总组数 = 该题命中率；
    命中率 >= 0.8 记为通过；总分 = 通过题数 / 总题数。
只用标准库，板端 python3 直接跑。
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path


def post(url, payload, timeout=600):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def score_one(answer, groups):
    hit, detail = 0, []
    for g in groups:
        found = [k for k in g if k and k in answer]
        if found:
            hit += 1
            detail.append(found[0])
        else:
            detail.append("-")
    return (hit / len(groups) if groups else 0.0), detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8097")
    ap.add_argument("--testset", default="工业监控固定测试集_v1.json")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--n-predict", type=int, default=512)
    ap.add_argument("--out", default="判分结果.json")
    ap.add_argument("--think", action="store_true", help="默认关闭 thinking（与测试集协议一致）")
    args = ap.parse_args()

    ts = json.loads(Path(args.testset).read_text(encoding="utf-8"))
    qs = ts["questions"]
    url = args.endpoint.rstrip("/") + "/v1/chat/completions"
    print(f"测试集：{ts.get('name')} v{ts.get('version')}  共 {len(qs)} 题 × {args.rounds} 轮")

    rows, t0 = [], time.time()
    for rd in range(1, args.rounds + 1):
        for q in qs:
            payload = {
                "messages": [{"role": "user", "content": q["prompt"]}],
                "temperature": 0.0,
                "top_k": 1,
                "max_tokens": args.n_predict,
                "chat_template_kwargs": {"enable_thinking": bool(args.think)},
            }
            try:
                r = post(url, payload)
                ans = (r.get("choices", [{}])[0].get("message", {}) or {}).get("content", "") or ""
                t = r.get("timings") or {}
            except Exception as e:  # 网络/超时都记成失败，不中断整轮
                ans, t = "", {"error": f"{type(e).__name__}: {e}"}
            rate, detail = score_one(ans, q.get("must_contain", []))
            rows.append({"round": rd, "id": q.get("id"), "category": q.get("category"),
                         "hit_rate": round(rate, 3), "passed": rate >= 0.8,
                         "hits": detail, "answer": ans[:1200],
                         "prompt_ms": t.get("prompt_ms"), "predicted_per_second": t.get("predicted_per_second"),
                         "error": t.get("error")})
            print(f"  R{rd} {q.get('id')} 命中 {rate:.0%} {'PASS' if rate >= 0.8 else 'fail'}")

    per_q = {}
    for r in rows:
        per_q.setdefault(r["id"], []).append(r["hit_rate"])
    summary = {
        "testset": ts.get("name"), "version": ts.get("version"),
        "rounds": args.rounds, "questions": len(qs),
        "pass_rate": round(sum(1 for r in rows if r["passed"]) / len(rows), 3) if rows else 0,
        "mean_hit_rate": round(sum(r["hit_rate"] for r in rows) / len(rows), 3) if rows else 0,
        "per_question_mean": {k: round(sum(v) / len(v), 3) for k, v in per_q.items()},
        "wall_s": round(time.time() - t0, 1),
    }
    out = {"summary": summary, "rows": rows}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n总通过率 {summary['pass_rate']:.1%}（{summary['rounds']} 轮 × {summary['questions']} 题）"
          f"，平均命中 {summary['mean_hit_rate']:.1%}；写出 {args.out}")


if __name__ == "__main__":
    main()
