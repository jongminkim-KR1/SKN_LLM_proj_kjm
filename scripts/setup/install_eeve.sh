#!/bin/bash
set -e

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# GPU 설정
echo "=== GPU 설정 ==="
export CUDA_VISIBLE_DEVICES=0
export OLLAMA_NUM_GPU=1
echo "GPU 0번 사용 설정 완료"

echo "=== Hugging Face CLI 설치 ==="
pip install --user huggingface-hub
export PATH="$HOME/.local/bin:$PATH"

echo "=== EEVE 모델 파일 다운로드 ==="
mkdir -p ./models

# Hugging Face 환경변수 설정 (토큰 추가 시 여기에)
export HF_HUB_DISABLE_PROGRESS_BARS=1

~/.local/bin/hf download heegyu/EEVE-Korean-Instruct-10.8B-v1.0-GGUF ggml-model-Q5_K_M.gguf \
  --local-dir ./models \
  --force-download \
  --quiet

echo "=== Modelfile 생성 중 ==="
cat << 'EOF' > Modelfile
FROM ./models/ggml-model-Q5_K_M.gguf

TEMPLATE """{{- if .System }}
<s>{{ .System }}</s>
{{- end }}
<s>Human:
{{ .Prompt }}</s>
<s>Assistant:
"""

SYSTEM """당신은 MLB 전문 야구 코치입니다.
세이버메트릭스(wRC+, FIP, ISO, K%, BB%, WAR, GB% 등)를 깊이 이해하고,
경기 상황을 분석하여 구체적이고 논리적인 전략을 제시합니다.
항상 데이터 기반으로 판단하며, 한국어로 명확하게 설명합니다."""

PARAMETER stop <s>
PARAMETER stop </s>
PARAMETER num_gpu 99
PARAMETER num_thread 4
EOF

echo "=== EEVE 모델 등록 중 ==="
ollama create EEVE-Korean-10.8B -f ./Modelfile

echo "EEVE-Korean-10.8B 모델 설치 완료!"
