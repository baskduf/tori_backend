# 🎯 랜덤통화 매칭 앱 백엔드 API 명세서 (Django)

---

## 1. 사용자(User) API

### 1.1 회원가입  
- URL: `/api/auth/signup/`  
- Method: `POST`  
- Request Body (multipart/form-data):  
  [ username: string, password: string, age: integer, gender: male|female, profile_image: file ]  
- Response:  
  [ message: string ]

---

### 1.2 로그인  
- URL: `/api/auth/login/`  
- Method: `POST`  
- Request Body:  
  [ username: string, password: string ]  
- Response:  
  [ access: string, refresh: string ]

---

### 1.3 로그아웃  
- URL: `/api/auth/logout/`  
- Method: `POST`  
- Request Body:  
  [ refresh: string ]  
- Response:  
  [ message: string ]

---

## 2. 매칭 조건 API

### 2.1 매칭 조건 저장  
- URL: `/api/match/settings/`  
- Method: `POST`  
- Request Body:  
  [ preferred_gender: male|female|all, age_range: [int, int], radius_km: int ]  
- Response:  
  [ message: string ]

---

## 3. 매칭 API

### 3.1 랜덤 매칭 요청  
- URL: `/api/match/random/`  
- Method: `GET`  
- Response:  
  [ matched_user: { username: string, age: int, gender: string, profile_image: string, rating: float }, show_time_sec: int ]

---

### 3.2 매칭 수락 / 거절  
- URL: `/api/match/decision/`  
- Method: `POST`  
- Request Body:  
  [ match_id: int, decision: accept|reject ]  
- Response:  
  [ status: matched|next ]

---

### 3.3 매칭 취소 
- URL: `/api/match/cancel/`  
- Method: `POST`  
- 설명:  
  로그인한 사용자의 `is_matching` 상태를 `False`로 변경하여 매칭 대기 상태를 해제합니다.  
- Request Body:  
  없음  
- Response:  
  [ "message": "매칭 상태가 해제되었습니다." ]

---

## 4. 통화 API

### 4.1 통화 시작  
- URL: `/api/call/start/`  
- Method: `POST`  
- Request Body:  
  [ match_id: int ]  
- Response:  
  [ call_session_id: string ]

---

### 4.2 통화 종료  
- URL: `/api/call/end/`  
- Method: `POST`  
- Request Body:  
  [ call_session_id: string ]  
- Response:  
  [ message: string ]

---

## 5. 평가 API

### 5.1 최근 통화 히스토리 조회  
- URL: `/api/history/recent/`  
- Method: `GET`  
- Response:  
  [ { username: string, call_time: datetime, call_id: int }, ... ]

---

### 5.2 상대 평가 등록  
- URL: `/api/history/rate/`  
- Method: `POST`  
- Request Body:  
  [ call_id: int, rating: int (1~5), comment: string ]  
- Response:  
  [ message: string ]

---

## 6. 보석(재화) API

### 6.1 보석 잔액 조회  
- URL: `/api/gem/balance/`  
- Method: `GET`  
- Response:  
  [ gems: int ]

---

### 6.2 보석 사용 (조건 매칭 시 자동 소모)  
- 자동 처리

---

### 6.3 보석 충전 요청  
- URL: `/api/gem/charge/`  
- Method: `POST`  
- Request Body:  
  [ payment_token: string ]  
- Response:  
  [ gems_added: int, new_balance: int ]

---

## 7. 기타

### 7.1 유저 프로필 조회  
- URL: `/api/user/profile/`  
- Method: `GET`  
- Response:  
  [ username: string, age: int, gender: string, profile_image: string ]

---

### 7.2 유저 프로필 수정  
- URL: `/api/user/profile/`  
- Method: `PUT`  
- Request Body (multipart/form-data):  
  [ username: string, profile_image: file ]  
- Response:  
  [ message: string ]

---

## 인증
- 모든 API는 JWT 인증 필요 (`Authorization: Bearer <access_token>`)
- WebSocket 연결 시에도 토큰 인증 필수

---