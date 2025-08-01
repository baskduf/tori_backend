<img width="300" height="300" alt="ChatGPT Image 2025년 7월 31일 오전 10_00_26" src="https://github.com/user-attachments/assets/dd3ad9a9-aa67-42f2-8573-3e86637f56ae" />

랜덤 통화 매칭 앱 백엔드
본 프로젝트는 Flutter 프론트엔드와 Django 백엔드를 사용하여 개발된 랜덤 통화 매칭 서비스의 서버 측 구현입니다.
사용자는 지정한 조건(성별, 나이, 반경)에 따라 무작위로 매칭되어 음성 통화를 할 수 있으며, 통화 종료 후 상대방을 평가할 수 있습니다.
또한, 보석(재화) 시스템을 통해 특정 조건 매칭 시 보석을 소모하고, 이를 충전할 수 있는 결제 기능이 포함되어 있습니다.

주요 기능

사용자 회원가입 및 JWT 기반 인증
사용자 프로필 관리 (닉네임, 나이, 성별, 프로필 이미지)
매칭 조건 설정 및 조건에 따른 랜덤 매칭
통화 시작 및 종료 관리
최근 통화 기록 및 상대방 평가 기능
보석 잔액 관리 및 충전, 사용 내역 기록

기술 스택
Backend: Django, Django REST Framework

인증: JWT (djangorestframework-simplejwt)

데이터베이스: PostgreSQL (또는 선택한 DB)

결제 연동: 외부 PG사 및 결제 토큰 처리 예정
