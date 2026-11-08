#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 claims.json：逐条重新打开证据文件、按表达式取值并与登记值比对。

本脚本为提交包内的独立版本：claims.json 与本脚本同级，证据文件在 results/。
用法：python tools/verify_claims.py
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
CLAIMS = os.path.join(PKG, "claims.json")
RESULTS = os.path.join(PKG, "results")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def split_top(expr, sep="|"):
    out, buf, depth, quote = [], [], 0, None
    for ch in expr:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch == "[":
            depth += 1
            buf.append(ch)
        elif ch == "]":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def resolve(d, expr):
    if "|" in expr:
        parts = split_top(expr)
        if len(parts) > 1:
            return [resolve(d, e) for e in parts]
    cur = d
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\[[^\]]*\]", expr):
        if tok.startswith("["):
            sel = tok[1:-1].strip()
            if "=" in sel:
                conds = dict(kv.split("=", 1) for kv in sel.split(","))
                hits = [x for x in cur if all(str(x.get(k)) == v for k, v in conds.items())]
                if len(hits) != 1:
                    raise KeyError(f"{tok} 命中 {len(hits)} 条")
                cur = hits[0]
            else:
                key = sel.strip("'\"")
                cur = cur[int(key)] if isinstance(cur, list) else cur[key]
        else:
            cur = cur[tok]
    return cur


def main():
    d = json.load(open(CLAIMS, encoding="utf-8"))
    bad = 0
    for c in d["claims"]:
        base = os.path.basename(c["evidence"])
        p = os.path.join(RESULTS, base)
        if not os.path.exists(p):
            print(f"  MISSING  {c['id']}  ({base})")
            bad += 1
            continue
        h = sha256(p)
        if c.get("evidence_sha256") and h != c["evidence_sha256"]:
            print(f"  SHA-DIFF {c['id']}")
            bad += 1
            continue
        try:
            v = resolve(json.load(open(p, encoding="utf-8")), c["expr"])
        except Exception as e:
            print(f"  EXPR-ERR {c['id']}  {type(e).__name__}: {e}")
            bad += 1
            continue
        if v != c["value"]:
            print(f"  VALUE-DIFF {c['id']}  table={c['value']} now={v}")
            bad += 1
    print(f"\n{len(d['claims']) - bad}/{len(d['claims'])} 通过，{bad} 条有问题")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
