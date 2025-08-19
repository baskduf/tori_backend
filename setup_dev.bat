@echo off
REM ==============================================
REM Django 개발 환경 세팅 배치 (Windows)
REM ==============================================

REM 1. 가상환경 생성
python -m venv venv

REM 2. 가상환경 활성화
call venv\Scripts\activate

REM 3. pip 최신 버전으로 업그레이드
python -m pip install --upgrade pip

REM 4. requirements.txt 설치
pip install -r requirements.txt

REM 5. DB 마이그레이션 적용
python manage.py makemigrations
python manage.py migrate

REM 6. Daphne 서버 실행 (ASGI)
daphne -b 0.0.0.0 -p 8000 tori_backend.asgi:application
