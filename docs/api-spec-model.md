# 🗃️ Django 모델 스펙 명세서

---

## 1. User 모델 (커스텀 유저 모델)

| 필드명          | 타입            | 설명                      | 비고                        |
|----------------|----------------|-------------------------|---------------------------|
| `username`     | CharField      | 로그인 아이디 (고유)          | `unique=True`              |
| `password`     | CharField      | 비밀번호 (해시 저장)           | Django 기본 패스워드 해시 사용  |
| `age`          | IntegerField   | 사용자 나이                  |                            |
| `gender`       | CharField      | 성별 (`male` / `female`)   | choices 설정                |
| `profile_image`| ImageField     | 프로필 이미지                 | 업로드 경로 지정 가능           |
| `date_joined`  | DateTimeField  | 가입일                      | 자동 생성                   |
| `is_active`    | BooleanField   | 활성 계정 여부                | 기본값 True                  |
| `is_staff`     | BooleanField   | 관리자 권한 여부              | 기본값 False                 |
| `is_matching`     | BooleanField   | 매칭 여부              | 기본값 False                 |

---

## 4. CallSession 모델

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `id`            | AutoField    | 통화 세션 고유 ID               | Primary Key                 |
| `user1`         | ForeignKey   | 통화 참여자 1 (User)           | `on_delete=models.CASCADE`  |
| `user2`         | ForeignKey   | 통화 참여자 2 (User)           | `on_delete=models.CASCADE`  |
| `started_at`    | DateTimeField| 통화 시작 시간                 | auto_now_add=True           |
| `ended_at`      | DateTimeField| 통화 종료 시간                 | null=True, blank=True        |
| `duration_sec`  | IntegerField | 통화 지속 시간 (초)             | 계산해서 저장                |

---

## 5. CallRating 모델

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `id`            | AutoField    | 평가 고유 ID                   | Primary Key                 |
| `call_session`  | ForeignKey   | 평가 대상 통화 세션             | `on_delete=models.CASCADE`  |
| `rater`         | ForeignKey   | 평가자 (User)                 | `on_delete=models.CASCADE`  |
| `ratee`         | ForeignKey   | 평가받는 사람 (User)           | `on_delete=models.CASCADE`  |
| `rating`        | IntegerField | 별점 (1~5)                   |                             |
| `comment`       | TextField    | 평가 코멘트                    | optional                    |
| `created_at`    | DateTimeField| 평가 등록 시간                 | auto_now_add=True           |

---

## 6. GemBalance 모델

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `user`          | OneToOneField| 유저별 보석 잔액 관리           | `on_delete=models.CASCADE`  |
| `balance`       | IntegerField | 보석 개수                     | 기본값 0                    |

---

## 7. GemTransaction 모델

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `id`            | AutoField    | 거래 고유 ID                   | Primary Key                 |
| `user`          | ForeignKey   | 거래 대상 유저                  | `on_delete=models.CASCADE`  |
| `amount`        | IntegerField | 증감 보석 개수 (음수 가능)       |                             |
| `reason`        | CharField    | 거래 이유 (`charge`, `use`, 등)  | choices 가능                 |
| `created_at`    | DateTimeField| 거래 발생 시간                 | auto_now_add=True           |

---