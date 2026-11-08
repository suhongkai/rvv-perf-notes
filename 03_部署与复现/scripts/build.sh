#!/bin/bash
# =============================================================================
# 从交付源码包重建二进制（K1 / Bianbu / GCC 14.2）
#
# 用法：
#   ./build.sh [源码目录] [构建目录]
#   ./build.sh                      # 当前目录就是源码树
#
# 源码包：llama-src-final-717a8ad8.tar.gz
#   SHA256 064fdd6fe3dae085b38821c5310679193bd147fd41d0a5d561b3afee9348742d
#   内含三处改动：Q4_1 repack、CONCAT 转置快速路径、GQA 折叠（= 补丁 01—03）
#   **要得到当前交付构建，还必须打补丁 07：chunk16（nth*4 → nth*16）**
#     本脚本会自动检测并应用 ../patches/07-chunk16-chunkmult.patch
#
# 产物指纹（与 MANIFEST.md 对照）：
#   交付构建 libggml-cpu.so.0.26.0
#     4436a9f45bcc298b6768d79fc2becff6570be7afa8a2076bfdf37092b0647730   （+ 补丁 07，chunk16）
#     717a8ad81527c3c2f2bdf0872fc08189f84bfbfbf8fb3ec8d7978ed99fb75c3f   （旧，未含 07）
#
# 注意：源码路径会被 __FILE__ 编进二进制，换路径编出的 SHA 会差几十字节，
#       但功能等价——用下面的自检验证即可。
# =============================================================================
set -euo pipefail

SRC="${1:-$PWD}"
BUILD="${2:-$SRC/build}"
PATCHES="$(cd "$(dirname "$0")/../patches" 2>/dev/null && pwd || true)"

echo "== 源码: $SRC"
echo "== 构建: $BUILD"

# 0) 若源码缺 chunk16，自动打补丁
if ! grep -q "GGML_CPU_CHUNK_MULT" "$SRC/ggml/src/ggml-cpu/repack.cpp" 2>/dev/null; then
    if [ -n "$PATCHES" ] && [ -f "$PATCHES/07-chunk16-chunkmult.patch" ]; then
        echo "== 应用补丁 07（chunk16）"
        ( cd "$SRC" && patch -p1 < "$PATCHES/07-chunk16-chunkmult.patch" )
    else
        echo "警告：源码里没有 chunk16，也找不到 patches/07-chunk16-chunkmult.patch"
        echo "      这样编出来的是旧构建（20.9 t/s 档），不是当前交付构建（25.3 t/s 档）"
    fi
fi

CC_BIN="${CC_BIN:-/usr/bin/gcc-14}"
CXX_BIN="${CXX_BIN:-/usr/bin/g++-14}"
for f in "$CC_BIN" "$CXX_BIN"; do
    [ -x "$f" ] || { echo "缺少编译器: $f（Bianbu 默认 gcc 是 13.2，需要自行装 gcc-14）"; exit 1; }
done

cmake -S "$SRC" -B "$BUILD" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER="$CC_BIN" \
    -DCMAKE_CXX_COMPILER="$CXX_BIN" \
    -DGGML_CPU_REPACK=ON \
    -DGGML_RVV=ON \
    -DGGML_RV_ZFH=ON \
    -DGGML_RV_ZICBOP=ON \
    -DGGML_RV_ZIHINTPAUSE=ON \
    -DGGML_RV_ZVFH=ON \
    -DGGML_RV_ZVFBFWMA=OFF \
    -DGGML_NATIVE=ON \
    -DGGML_OPENMP=ON \
    -DGGML_BUILD_EXAMPLES=OFF \
    -DGGML_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=OFF \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_SERVER=ON

cmake --build "$BUILD" -j"$(nproc)" \
    --target llama-bench llama-server llama-quantize llama-perplexity llama-tokenize

echo
echo "== 产物指纹"
sha256sum "$BUILD/bin/libggml-cpu.so.0.26.0"

echo
echo "== 自检 1/4：Q4_1 repack 内核"
n=$(nm -D --defined-only "$BUILD/bin/libggml-cpu.so.0.26.0" | grep -c q4_1_16x1 || true)
echo "   q4_1_16x1 符号数 = $n（应为 2）"
[ "$n" -eq 2 ] || { echo "   失败：Q4_1 内核没编进去"; exit 1; }

echo "== 自检 2/4：GQA 折叠"
n=$(nm -D --defined-only "$BUILD/bin/libggml-cpu.so.0.26.0" | grep -c ggml_vec_dot_f16_multi || true)
echo "   ggml_vec_dot_f16_multi 符号数 = $n（应为 1）"
[ "$n" -eq 1 ] || { echo "   失败：GQA 折叠没编进去"; exit 1; }

echo "== 自检 3/4：CONCAT 快速路径"
n=$(grep -c 'CONCAT' "$SRC/ggml/src/ggml-cpu/ops.cpp" || true)
echo "   ops.cpp 中 CONCAT 相关行数 = $n（应 ≥1）"
[ "$n" -ge 1 ] || { echo "   失败：CONCAT 补丁不在源码里"; exit 1; }

echo "== 自检 4/4：chunk16"
n=$(grep -c 'GGML_CPU_CHUNK_MULT' "$SRC/ggml/src/ggml-cpu/repack.cpp" || true)
echo "   repack.cpp 中 GGML_CPU_CHUNK_MULT 出现 $n 次（应 ≥1）"
[ "$n" -ge 1 ] || { echo "   失败：chunk16 补丁没打上，编出来是旧构建"; exit 1; }

echo
echo "OK：四项自检全部通过"
