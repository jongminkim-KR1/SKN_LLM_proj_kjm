#!/bin/bash
set -e

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

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

SYSTEM """A chat between a curious user and an artificial intelligence assistant. 
The assistant gives helpful, detailed, and polite answers to the user's questions."""

PARAMETER stop <s>
PARAMETER stop </s>
EOF

echo "=== EEVE 모델 등록 중 ==="
ollama create EEVE-Korean-10.8B -f ./Modelfile

echo "EEVE-Korean-10.8B 모델 설치 완료!"
