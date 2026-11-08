#!/bin/bash
# =============================================================================
# 从官方原始权重生成部署模型（GGUF Q4_0，输出头/词嵌入保持 Q6_K）
#
# 为什么要显式指定 Q6_K：Qwen3.5 的 `token_embd.weight` 同时充当输出头（tie_word_embeddings），
# 占 27%（2B）/15%（4B）的参数。把它降到 Q4_0 会让 PPL 恶化 +1.6%（2B）/+1.3%（4B），
# 超过我们自定的 1.5% 质量门槛；保持 Q6_K 则是"质量几乎不动、速度不降"的选择。
#
# 用法：
#   ./quantize.sh <官方HF目录> <输出.gguf> <llama.cpp源码目录> [线程数]
# 例：
#   ./quantize.sh ~/models/Qwen3.5-2B ~/out/Qwen3.5-2B-Q4_0.gguf ~/spacemit-llama 8
#
# 依赖：python3（含 torch/safetensors/numpy）、llama.cpp 的 convert_hf_to_gguf.py 与 llama-quantize。
# 说明：转换默认输出 f16 中间文件（约 2 倍体积），量化完成后可删除。
# =============================================================================
set -euo pipefail

HF="${1:?用法: $0 <官方HF目录> <输出.gguf> <llama.cpp目录> [线程数]}"
OUT="${2:?缺少输出路径}"
LLAMA="${3:?缺少 llama.cpp 目录}"
JOBS="${4:-$(nproc)}"
PY="${PY:-python3}"

F16="${OUT%.gguf}-f16.gguf"

echo "== [1/3] 官方权重 → f16 GGUF"
echo "   输入: $HF"
"$PY" "$LLAMA/convert_hf_to_gguf.py" "$HF" --outtype f16 --no-mtp --outfile "$F16"

echo "== [2/3] f16 GGUF → Q4_0（输出头/词嵌入 Q6_K）"
# 选项必须写在位置参数之前，否则 llama-quantize 会拒绝
LD_LIBRARY_PATH="$LLAMA/build/bin" "$LLAMA/build/bin/llama-quantize" \
    --output-tensor-type Q6_K --token-embedding-type Q6_K \
    "$F16" "$OUT" Q4_0 "$JOBS"

echo "== [3/3] 产物指纹"
stat -c '%s %n' "$OUT"
sha256sum "$OUT"
echo
echo "中间文件 $F16 可删除（$(stat -c %s "$F16") 字节）"
