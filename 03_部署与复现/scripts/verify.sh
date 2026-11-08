#!/bin/bash
# =============================================================================
# 交付物自检：模型/二进制指纹 + 一次基准跑分
#
# 用法：
#   ./verify.sh <模型gguf> [板端 llama.cpp 目录]
# 例：
#   ./verify.sh Qwen3.5-2B-Q4_0-selfmade.gguf ~/labdeploy/build/spacemit-llama
#
# **只认 chunk16 交付构建**（lib 里必须含补丁 07 的 GGML_CPU_CHUNK_MULT 标记）。
# 查找顺序（第一个命中的就用，全部不命中直接报错）：
#   ① $BIN_DIR（显式指定）
#   ② <llama.cpp目录>/chunk16-build/bin
#   ③ 07_源码与二进制/chunk16/bin（deploy.sh 解包后的交付 bin）
#   ④ <llama.cpp目录>/build/bin（仅当 lib 里含 chunk16 标记）
# 旧构建 build-final（717a8ad8，20.9 / 7.46 档）**不再回退**——那组数字会被判失败。
#
# 期望（K1 8GB、-ub 128、-fa 0；与 README §四、主报告 §五 同一口径）：
#   2B Q4_0：pp512 ≈ 24.4—26.9 t/s；tg128（t8@512）≈ 3.7—4.1；tg128（t7 零深度）≈ 4.1—4.6
#   4B Q4_0（预填 3 板中位 9.84）：pp512 ≈ 9.4—10.5；tg128（t8@512）≈ 1.7—1.9；tg128（t7 零深度）≈ 1.9—2.1
#   板间漂移 5—9% 属正常（8 板 IQR 0.6，约 2.2%），看量级即可。
# =============================================================================
set -euo pipefail

MODEL="${1:?用法: $0 <模型gguf> [llama.cpp目录]}"
ROOT="${2:-$HOME/labdeploy/build/spacemit-llama}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DELIVERY="${HERE}/../07_源码与二进制/chunk16/bin"   # deploy.sh 解包后的交付 bin
LIB="libggml-cpu.so.0.26.0"
DELIVERY_PREFIX="4436a9f4"
OLD_PREFIX="717a8ad8"

# chunk16 判据：补丁 07 用 getenv("GGML_CPU_CHUNK_MULT") 读分块倍率，
# 这个字符串必然留在 libggml-cpu 里；旧构建没有它。
is_chunk16() {
    local lib="$1/$LIB"
    [ -f "$lib" ] && grep -q 'GGML_CPU_CHUNK_MULT' "$lib" 2>/dev/null
}

pick_bin() {
    local d
    for d in "$@"; do
        [ -n "$d" ] || continue
        if [ -x "$d/llama-bench" ] && is_chunk16 "$d"; then
            echo "$d"
            return 0
        fi
    done
    return 1
}

if [ -n "${BIN_DIR:-}" ]; then
    BIN="$BIN_DIR"
    if ! is_chunk16 "$BIN"; then
        echo "错误：$BIN 不是 chunk16 构建（lib 里没有 GGML_CPU_CHUNK_MULT 标记）"
        echo "      请用交付 bin；旧构建 build-final 跑出来是 20.9 / 7.46 档，会被判失败。"
        exit 1
    fi
elif BIN="$(pick_bin "$ROOT/chunk16-build/bin" "$DELIVERY" "$ROOT/build/bin")"; then
    :
else
    echo "错误：找不到 chunk16 交付构建，已查："
    echo "      \$BIN_DIR（未设置）"
    echo "      $ROOT/chunk16-build/bin"
    echo "      $DELIVERY"
    echo "      $ROOT/build/bin"
    echo "      请用交付 bin：解包 ../07_源码与二进制/llama-bin-chunk16-4436a9f4.tar.gz"
    echo "      （deploy.sh 会自动解到 07_源码与二进制/chunk16/bin），"
    echo "      或用 build.sh 重建到 chunk16-build/ 后重跑；"
    echo "      **不要用旧构建 build-final（717a8ad8，20.9 t/s 档）。**"
    exit 1
fi
echo "== 使用构建: $BIN"
if [ -x "$ROOT/build-final/bin/llama-bench" ]; then
    echo "   （已忽略旧构建 $ROOT/build-final/bin —— 只认 chunk16）"
fi

echo "== 二进制指纹"
LIB_SHA="$(sha256sum "$BIN/$LIB" | cut -d' ' -f1)"
echo "libggml-cpu: $LIB_SHA"
case "$LIB_SHA" in
    "$DELIVERY_PREFIX"*) echo "   = 交付构建 $DELIVERY_PREFIX（chunk16）" ;;
    "$OLD_PREFIX"*)      echo "   失败：这是旧构建 $OLD_PREFIX（20.9 / 7.46 档），不是交付构建"; exit 1 ;;
    *)                   echo "   = 本地新编（功能等价；源码路径不同会让 SHA 差几十字节）" ;;
esac
echo -n "q4_1_16x1 符号数: "; nm -D --defined-only "$BIN/$LIB" | grep -c q4_1_16x1 || true
echo -n "GQA 符号数: "; nm -D --defined-only "$BIN/$LIB" | grep -c ggml_vec_dot_f16_multi || true
echo -n "chunk16 标记: "; grep -c 'GGML_CPU_CHUNK_MULT' "$BIN/$LIB" || true

echo
echo "== 模型指纹"
M="$MODEL"
[ -f "$M" ] || M="$HOME/labdeploy/models/$MODEL"
sha256sum "$M"
stat -c '%s 字节' "$M"

echo
echo "== 清理残留进程"
pkill -x llama-bench 2>/dev/null || true
sleep 1

echo "== 基准 1/2：prefill pp512 + decode tg128（8 线程，t8@512，ub128，fa0）"
cd "$BIN"
LD_LIBRARY_PATH="$BIN" ./llama-bench -m "$M" -p 512 -n 128 -t 8 -ub 128 -r 3 -fa 0

echo
echo "== 基准 2/2：decode 零深度（7 线程，t7，ub128，fa0）"
LD_LIBRARY_PATH="$BIN" ./llama-bench -m "$M" -p 0 -n 128 -t 7 -ub 128 -r 4 -fa 0

echo
echo "== 完成。若 pp512 / tg128 落在上面注明的区间内，即为正常。"
echo "   （pp512 ≈ 20.9 / 7.46 说明跑的是**旧构建**，不是交付构建 25.3 / 9.84 档。）"
