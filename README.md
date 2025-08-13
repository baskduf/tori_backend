# TORI - 새로운 인연과의 만남

TORI는 실시간 음성 채팅을 통해 새로운 사람들과 만날 수 있는 매칭 앱입니다. 사용자의 선호도(나이, 성별, 거리)를 기반으로 적합한 상대를 찾아 실시간 음성 통화를 제공합니다.

## 🎯 주요 기능

- **사용자 인증**: 안전한 회원가입 및 로그인
- **매칭 설정**: 나이, 성별, 반경(km) 기반 선호도 설정
- **실시간 매칭**: 설정에 맞는 사용자와의 즉시 매칭
- **음성 통화**: WebRTC 기반 고품질 음성 채팅
- **안전한 환경**: 익명성 보장 및 사용자 보호

## 🏗️ 기술 스택

### Backend
- **Django** - RESTful API 및 비즈니스 로직
- **Django Channels** - WebSocket 실시간 통신
- **Redis** - 매칭 큐 및 캐시 관리
- **PostgreSQL** - 사용자 데이터 및 설정 저장

### Frontend
- **Flutter** - 크로스 플랫폼 모바일 앱
- **WebRTC** - 실시간 음성 통화
- **WebSocket** - 실시간 매칭 알림

## 📱 스크린샷

| 로그인 | 매칭 설정 | 매칭 대기 | 음성 통화 |
|--------|-----------|-----------|-----------|
| <img src="screenshots/login.png" width="200"> | <img src="screenshots/settings.png" width="200"> | <img src="screenshots/matching.png" width="200"> | <img src="screenshots/call.png" width="200"> |

## 🚀 시작하기

### 필수 요구사항

- **Backend**: Python 3.9+, Django 4.2+, Redis 6.0+
- **Frontend**: Flutter 3.10+, Dart 3.0+
- **Database**: PostgreSQL 13+

### Backend 설치 및 실행

```bash
# 저장소 클론
git clone https://github.com/yourusername/tori.git
cd tori

# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r backend/requirements.txt

# 환경 변수 설정
cp backend/.env.example backend/.env
# .env 파일을 편집하여 데이터베이스 및 Redis 설정

# 데이터베이스 마이그레이션
cd backend
python manage.py migrate

# Redis 서버 시작 (별도 터미널)
redis-server

# Django 서버 실행
python manage.py runserver
```

### Frontend 설치 및 실행

```bash
# Flutter 앱 디렉토리로 이동
cd frontend

# 패키지 설치
flutter pub get

# 앱 실행 (디바이스 연결 필요)
flutter run
```

## 🔧 환경 설정

### Backend 환경 변수 (.env)

```env
# Django 설정
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 데이터베이스 설정
DB_NAME=tori_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis 설정
REDIS_URL=redis://localhost:6379

# CORS 설정
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend 설정 (lib/config/app_config.dart)

```dart
class AppConfig {
  static const String baseUrl = 'http://localhost:8000';
  static const String wsUrl = 'ws://localhost:8000';
  static const String appName = 'TORI';
}
```

## 📁 프로젝트 구조

```
tori/
├── backend/
│   ├── apps/
│   │   ├── accounts/          # 사용자 인증
│   │   ├── matching/          # 매칭 시스템
│   │   └── voice_chat/        # 음성 채팅
│   ├── config/                # Django 설정
│   ├── requirements.txt
│   └── manage.py
├── frontend/
│   ├── lib/
│   │   ├── screens/           # UI 화면
│   │   ├── services/          # API 서비스
│   │   ├── models/            # 데이터 모델
│   │   └── widgets/           # 재사용 위젯
│   ├── pubspec.yaml
│   └── README.md
├── docs/                      # 문서
├── screenshots/               # 앱 스크린샷
└── README.md
```

## 🎮 사용 방법

### 1. 회원가입 및 로그인
1. 앱을 실행하고 "회원가입" 버튼을 탭
2. 필수 정보 입력 (아이디, 비밀번호, 나이, 성별)
3. 계정 생성 후 로그인

### 2. 매칭 설정
1. 프로필 화면에서 "매칭 설정" 선택
2. 선호하는 상대방의 나이 범위 설정
3. 선호 성별 선택 (남성/여성/무관)
4. 매칭 반경(km) 설정

### 3. 매칭 및 음성 통화
1. 홈 화면에서 "매칭 시작" 버튼 탭
2. 조건에 맞는 상대방과 매칭될 때까지 대기
3. 매칭 완료 시 음성 통화 자동 시작
4. 통화 종료 후 새로운 매칭 가능

## 🔒 보안 및 개인정보

- **익명성**: 실명이 아닌 닉네임 사용
- **위치 정보**: 정확한 위치가 아닌 대략적 거리만 사용
- **데이터 암호화**: 모든 통신 데이터 암호화
- **자동 삭제**: 통화 기록 자동 삭제

## 🧪 테스트

### Backend 테스트

```bash
cd backend
python manage.py test
```

### Frontend 테스트

```bash
cd frontend
flutter test
```

## 📈 성능 모니터링

- **Redis 모니터링**: 매칭 큐 및 온라인 사용자 수 추적
- **WebSocket 연결**: 실시간 연결 상태 모니터링
- **매칭 성공률**: 매칭 성공/실패 비율 분석

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 👥 개발팀

- **개발자**: [Your Name](https://github.com/yourusername)
- **이메일**: your.email@example.com

## 🔮 로드맵

### v1.1 (예정)
- [ ] 그룹 음성 채팅 (3-4명)
- [ ] 관심사 기반 매칭
- [ ] 사용자 신고 기능

### v1.2 (예정)
- [ ] 텍스트 채팅 기능
- [ ] 프로필 사진 업로드
- [ ] 매칭 히스토리

## ⚠️ 알려진 이슈

- iOS에서 백그라운드 음성 통화 제한
- 일부 Android 기기에서 권한 문제

## 📞 지원

문제가 발생하거나 질문이 있으시면:
- [Issues](https://github.com/yourusername/tori/issues) 페이지에서 버그 리포트
- [Discussions](https://github.com/yourusername/tori/discussions)에서 질문 및 토론

---

<div align="center">

**TORI와 함께 새로운 인연을 만나보세요! 💝**

[다운로드](https://github.com/yourusername/tori/releases) | [문서](https://github.com/yourusername/tori/wiki) | [데모](https://tori-demo.herokuapp.com)

</div>
