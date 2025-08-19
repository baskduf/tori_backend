#!/bin/bash
# ==============================================
# Django 개발 환경 + Redis 세팅 스크립트 (Linux/macOS)
# ==============================================

# 1. 가상환경 생성
python3 -m venv venv

# 2. 가상환경 활성화
source venv/bin/activate

# 3. pip 최신 버전으로 업그레이드
pip install --upgrade pip

# 4. requirements.txt 설치
pip install -r requirements.txt

# 5. DB 마이그레이션 적용
python manage.py makemigrations
python manage.py migrate

# 6. Redis 서버 실행 (백그라운드)
if ! command -v redis-server &> /dev/null
then
    echo "Redis가 설치되어 있지 않습니다. 설치 후 다시 시도하세요."
    exit 1
fi
redis-server --daemonize yes
echo "Redis 서버 실행 완료"

# 7. Daphne 서버 실행 (ASGI)
daphne -b 0.0.0.0 -p 8000 tori_backend.asgi:application
