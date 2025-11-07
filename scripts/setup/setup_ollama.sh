#!/bin/bash
set -e

echo "=== 시스템 패키지 설치 중 ==="
apt update && apt install -y lshw curl

echo "=== Ollama 설치 중 ==="
curl -fsSL https://ollama.com/install.sh | sh

echo "=== Ollama 서버 백그라운드 실행 ==="
nohup ollama serve > ollama.log 2>&1 &
sleep 10

echo "=== Ollama 서버 기동 확인 ==="
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    echo "Waiting for Ollama server..."
    sleep 3
done
echo "Ollama server is ready!"
