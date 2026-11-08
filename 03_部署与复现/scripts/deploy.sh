#!/bin/bash
# =============================================================================
# 一键部署到 K1 板：解包交付二进制 + 推模型 → 校验 SHA256（不符即停止）→ 起服务 → 冒烟
#
# 用法：
#   ./deploy.sh <板IP> [模型gguf] [板端目录]
# 例：
#   ./deploy.sh <板IP> Qwen3.5-2B-Q4_0-selfmade.gguf
#
# 前置：
#   1. 板端用户 bianbu，SSH 可登录（首次请 ssh-copy-id）
#   2. **模型需先按 05_模型与测试集/05_模型与测试集.md §2 从网盘下载**，
#      放到 ../05_模型与测试集/models/ 下（默认就从那里取）；或用 MODELS_DIR=<目录> 指定。
#   3. 交付二进制的 tar 包在 ../07_源码与二进制/llama-bin-chunk16-4436a9f4.tar.gz
#      （缺失时可用 build.sh 从源码重建，再用 BIN_DIR=<dir> 指定）
# =============================================================================
set -euo pipefail

HOST="${1:?用法: $0 <板IP> [模型gguf] [板端目录]}"
MODEL="${2:-Qwen3.5-2B-Q4_0-selfmade.gguf}"
DEST="${3:-/home/bianbu/labdeploy}"

HERE="$(cd "$(dirname "$0")/.." && pwd)"          # 03_部署与复现
PKG="$(cd "${HERE}/.." && pwd)"                    # 提交包根目录
BIN_ROOT="${PKG}/07_源码与二进制"
BIN="${BIN_DIR:-${BIN_ROOT}/chunk16/bin}"          # 首次运行自动解包到这里
MODELS="${MODELS_DIR:-${PKG}/05_模型与测试集/models}"

LIB="libggml-cpu.so.0.26.0"
LIB_SHA_EXPECT="4436a9f45bcc298b6768d79fc2becff6570be7afa8a2076bfdf37092b0647730"

# ---- 前置检查（在碰板子之前就把话说清楚）----
if [ ! -f "${MODELS}/${MODEL}" ]; then
  echo "错误：找不到模型 ${MODELS}/${MODEL}"
  echo "      请按 ../05_模型与测试集/05_模型与测试集.md §2 的网盘链接下载，"
  echo "      放到 ${MODELS}/ 下，或：MODELS_DIR=<模型所在目录> $0 $HOST $MODEL"
  exit 2
fi

if [ ! -x "${BIN}/llama-server" ]; then
  TGZ="${BIN_ROOT}/llama-bin-chunk16-4436a9f4.tar.gz"
  if [ -f "$TGZ" ]; then
    mkdir -p "$BIN"
    tar xzf "$TGZ" -C "$BIN"
  else
    echo "错误：既没有 ${BIN}/llama-server，也没有 ${TGZ}"
    echo "      请先用 build.sh 从源码构建，然后 BIN_DIR=<...>/bin $0 $HOST $MODEL"
    exit 2
  fi
fi

LOCAL_SHA="$(sha256sum "${BIN}/${LIB}" | cut -d' ' -f1)"
if [ "$LOCAL_SHA" != "$LIB_SHA_EXPECT" ]; then
  echo "错误：本地交付二进制指纹不符（这是不是交付构建？）"
  echo "      期望 $LIB_SHA_EXPECT"
  echo "      实得 $LOCAL_SHA"
  exit 3
fi

SSH="ssh -o StrictHostKeyChecking=no"
SCP="scp -o StrictHostKeyChecking=no"
PORT=8097

echo "== 目标 $HOST:$DEST  模型 $MODEL  端口 $PORT"

echo "== [1/4] 推送二进制与模型"
$SSH "bianbu@$HOST" "mkdir -p $DEST/build/spacemit-llama/build/bin $DEST/models"
$SCP -r "$BIN"/* "bianbu@$HOST:$DEST/build/spacemit-llama/build/bin/"
$SCP "${MODELS}/${MODEL}" "bianbu@$HOST:$DEST/models/"

echo "== [2/4] 校验（不符即停止，不会起服务）"
REMOTE_SHA="$($SSH "bianbu@$HOST" "sha256sum $DEST/build/spacemit-llama/build/bin/${LIB}" | cut -d' ' -f1)"
echo "   libggml-cpu sha256: $REMOTE_SHA"
if [ "$REMOTE_SHA" != "$LIB_SHA_EXPECT" ]; then
  echo "错误：板端二进制指纹与交付不符，已停止（未启动服务）"
  exit 4
fi
$SSH "bianbu@$HOST" "cd $DEST/models && sha256sum $MODEL" | sed 's/^/   模型 sha256: /'

echo "== [3/4] 起服务（-fa 0，与报告/verify.sh 同口径；预填 t8 / 生成 t7）"
$SSH "bianbu@$HOST" "pkill -x llama-server 2>/dev/null; sleep 1; \
  cd $DEST/build/spacemit-llama/build/bin && \
  nohup env LD_LIBRARY_PATH=. ./llama-server -m $DEST/models/$MODEL \
    -c 4096 -t 7 --threads-batch 8 -ub 128 -b 2048 -fa 0 -np 1 \
    --host 0.0.0.0 --port ${PORT} > /tmp/deploy-server.log 2>&1 & echo started"

echo "== [4/4] 冒烟（等 40 s 后请求一次）"
sleep 40
$SSH "bianbu@$HOST" "curl -s http://127.0.0.1:${PORT}/completion -H 'Content-Type: application/json' \
  -d '{\"prompt\":\"用一句话说明工业温度报警的处理流程\",\"n_predict\":48,\"temperature\":0}' \
  | head -c 400; echo"

echo
echo "服务地址: http://$HOST:${PORT}   日志: /tmp/deploy-server.log"
echo "下一步: ./verify.sh ${MODEL}"
