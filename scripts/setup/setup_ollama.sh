#!/bin/bash
set -e

echo "=== 시스템 패키지 설치 중 ==="
apt update && apt install -y lshw curl

echo "=== Ollama 설치 중 ==="
curl -fsSL https://ollama.com/install.sh | sh

# GPU 확인
if command -v nvidia-smi &> /dev/null; then
    echo "=== GPU 감지됨 ==="
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "경고: nvidia-smi를 찾을 수 없습니다. CPU 모드로 실행됩니다."
fi

echo "=== Ollama 서버 백그라운드 실행 (GPU 활성화) ==="
# GPU 환경변수를 직접 전달
nohup bash -c "CUDA_VISIBLE_DEVICES=0 ollama serve" > ollama.log 2>&1 &
sleep 10

echo "=== Ollama 서버 기동 확인 ==="
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    echo "Waiting for Ollama server..."
    sleep 3
done
echo "Ollama server is ready!"
