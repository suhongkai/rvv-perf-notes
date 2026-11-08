# -*- coding: utf-8 -*-
"""从 claims.json 生成技术报告的「附录 E claim 索引」并插入 02_技术报告.md。"""
import io
import json
import os
import re

R = r"F:\1\RISC-V工业监控_新赛事规划"
CL = os.path.join(R, "09_汇报文档", "claims.json")
MD = os.path.join(R, "11_提交_2026-11-08", "02_技术报告", "02_技术报告.md")

d = json.load(open(CL, encoding="utf-8"))
claims = d["claims"]


def short(s, n=34):
    s = s.replace("**", "").replace("`", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("|", "/")
    return s if len(s) <= n else s[: n - 1] + "…"


def fmt(v):
    if isinstance(v, list):
        parts = []
        for x in v:
            if isinstance(x, float):
                parts.append(f"{x:.1f}" if abs(x) >= 1000 else f"{x:g}")
            else:
                parts.append(str(x))
        return " / ".join(parts)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


rows = []
for c in claims:
    cid = c["id"].split("-")[0]
    ev = os.path.basename(c["evidence"])
    rows.append((cid, short(c["statement"]), fmt(c["value"]), ev))

lines = ["## 附录 E claim 索引", "",
         "下表为 `08_证据与复验/claims.json` 的逐条摘要（97 条），完整字段（SHA256、取值表达式、构建标签、取代关系）见该文件。", "",
         "**表 7 claim 索引**", "",
         "| 编号 | 内容摘要 | 登记值 | 证据文件 |",
         "|---|---|---|---|"]
for cid, st, val, ev in rows:
    lines.append(f"| {cid} | {st} | {val} | `{ev}` |")
lines += ["", "---", ""]

block = "\n".join(lines)

s = io.open(MD, encoding="utf-8").read()
# 已存在则替换，否则插在最后一行免责声明前
marker = "## 附录 E claim 索引"
if marker in s:
    head = s.split(marker)[0]
    tail = s.split("*本文所有数字以")
    s = head + block + "*本文所有数字以" + tail[-1]
else:
    s = s.replace("*本文所有数字以", block + "*本文所有数字以")
io.open(MD, "w", encoding="utf-8", newline="").write(s)
print("appendix rows:", len(rows))
