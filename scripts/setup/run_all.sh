#!/bin/bash
set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/../.."

echo "=== Ollama & EEVE-Korean 자동 설치 스크립트 ==="
echo ""

echo "=== 1단계: Ollama 설치 및 서버 시작 ==="
bash scripts/setup/setup_ollama.sh

echo ""
echo "=== 2단계: EEVE-Korean-10.8B 모델 설치 ==="
bash scripts/setup/install_eeve.sh

echo ""
echo "=== 모든 설치 완료! ==="
echo "Ollama 서버가 실행 중이며, EEVE-Korean-10.8B 모델이 설치되었습니다."
echo ""
echo "다음 명령어로 게임을 실행하세요:"
echo "필요한 라이브러리 설치"
bash pip install -r requirements.txt
echo "  streamlit run app.py"
