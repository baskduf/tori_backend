# 🗃️ Django 모델 스펙 명세서

---

## 1. User 모델 (커스텀 유저 모델)

| 필드명          | 타입            | 설명                      | 비고                        |
|----------------|----------------|-------------------------|---------------------------|
| `id`           | AutoField      | 사용자 고유 ID              | Primary Key                |
| `username`     | CharField      | 로그인 아이디 (고유)          | `unique=True`              |
| `password`     | CharField      | 비밀번호 (해시 저장)           | Django 기본 패스워드 해시 사용  |
| `age`          | IntegerField   | 사용자 나이                  | 매칭 호환성 검사에 사용        |
| `gender`       | CharField      | 성별 (`male` / `female`)   | 매칭 선호도 검사에 사용        |
| `date_joined`  | DateTimeField  | 가입일                      | 자동 생성                   |
| `is_active`    | BooleanField   | 활성 계정 여부                | 기본값 True                  |
| `is_staff`     | BooleanField   | 관리자 권한 여부              | 기본값 False                 |

**관계:**
- MatchSetting과 1:1 관계 (OneToOneField)
- MatchHistory와 다대다 관계 (Many-to-Many through intermediate table)
- MatchedRoom과 다대다 관계 (user1, user2로 참여)

---

## 2. MatchSetting 모델

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `id`            | AutoField    | 설정 고유 ID                   | Primary Key                 |
| `user`          | OneToOneField| User와 1:1 관계                | `on_delete=models.CASCADE`  |
| `age_min`       | PositiveIntegerField | 선호 최소 나이            | 기본값: 18                   |
| `age_max`       | PositiveIntegerField | 선호 최대 나이            | 기본값: 99                   |
| `radius_km`     | PositiveIntegerField | 반경(킬로미터 단위)       | 기본값: 1 (현재 미사용)        |
| `preferred_gender` | CharField  | 선호 성별                   | choices: `male`, `female`, `any` (기본값: `any`) |

**매칭 호환성 로직:**
- 나이: 양방향 범위 체크 (내가 상대방을, 상대방이 나를 수용)
- 성별: 양방향 선호도 체크 (`any`는 모든 성별 수용)

---

## 3. MatchHistory 모델

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `id`            | AutoField    | 매칭 히스토리 고유 ID           | Primary Key                 |
| `user1`         | ForeignKey   | 매칭 참여자 1                  | `on_delete=models.CASCADE`, `related_name='match_histories_1'` |
| `user2`         | ForeignKey   | 매칭 참여자 2                  | `on_delete=models.CASCADE`, `related_name='match_histories_2'` |
| `matched_at`    | DateTimeField| 매칭 성사 시간                 | `auto_now_add=True`         |

**제약조건:**
- `unique_together = (('user1', 'user2'),)`: 동일한 사용자 조합의 중복 매칭 방지

---

## 4. MatchedRoom 모델

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `id`            | AutoField    | 매칭된 방 고유 ID               | Primary Key                 |
| `user1`         | ForeignKey   | 방 참여자 1                    | `on_delete=models.CASCADE`, `related_name='matched_user1'` |
| `user2`         | ForeignKey   | 방 참여자 2                    | `on_delete=models.CASCADE`, `related_name='matched_user2'` |
| `matched_at`    | DateTimeField| 방 생성 시간                   | `auto_now_add=True`         |

**사용 목적:**
- 성공적인 매칭 후 음성 채팅 방 관리
- WebRTC 시그널링을 위한 방 식별자 제공

---

## 5. MatchQueue 모델 (정의되었으나 실제로는 Redis 사용)

| 필드명          | 타입           | 설명                       | 비고                          |
|-----------------|----------------|----------------------------|------------------------------|
| `id`            | AutoField      | 큐 엔트리 고유 ID           | Primary Key                   |
| `user`          | OneToOneField  | User와 1:1 관계             | `on_delete=models.CASCADE`    |
| `is_active`     | BooleanField   | 매칭 활성 상태              | 기본값 `True`                 |
| `entered_at`    | DateTimeField  | 대기열 진입 시간            | `auto_now_add=True`           |

**실제 구현:**
- 모델은 정의되어 있으나 실제로는 **Redis Sorted Set** 사용
- Redis 키: `match_queue`
- Score: 타임스탬프 (FIFO 순서 보장)

---

## 6. MatchRequest 모델 (정의되었으나 실제로는 Redis 사용)

| 필드명           | 타입          | 설명                          | 비고                         |
|-----------------|--------------|-----------------------------|-----------------------------|
| `id`            | AutoField    | 매칭 요청 고유 ID               | Primary Key                 |
| `from_user`     | ForeignKey   | 매칭 요청자                    | `on_delete=models.CASCADE`, `related_name='from_requests'` |
| `to_user`       | ForeignKey   | 매칭 대상자                    | `on_delete=models.CASCADE`, `related_name='to_requests'` |
| `status`        | CharField    | 상태                          | choices: `pending`, `accepted`, `rejected`, `matched` |
| `created_at`    | DateTimeField| 요청 생성 시간                 | `auto_now_add=True`          |

**실제 구현:**
- 모델은 정의되어 있으나 실제로는 **Redis JSON 데이터** 사용
- Redis 키: `match_requests:{match_id}`
- TTL: 300초 (5분 후 자동 만료)

---

## 7. Redis 데이터 구조 (실제 사용되는 매칭 데이터)

### 7.1 사용자 온라인 상태
```
키: user_online:{user_id}
타입: String
값: True
TTL: 60초
```

### 7.2 매칭 대기열
```
키: match_queue
타입: Sorted Set
멤버: user_id (string)
스코어: timestamp (float)
```

### 7.3 매치 데이터
```
키: match_requests:{match_id}
타입: String (JSON)
TTL: 300초

JSON 구조:
{
    "match_id": "123:456",
    "user1": "123",
    "user2": "456", 
    "user1_name": "alice",
    "user2_name": "bob",
    "status": "pending",
    "created_at": 1234567890,
    "updated_at": 1234567890,
    "user1_response": null,  // "accept" | "reject" | null
    "user2_response": null   // "accept" | "reject" | null
}
```

### 7.4 사용자별 현재 매치
```
키: user_matches:{user_id}
타입: String
값: match_id
TTL: 300초
```

### 7.5 전역 매칭 락
```
키: global_match_lock
타입: String
값: user_id (락을 획득한 사용자)
TTL: 10초
```

---

## 8. 데이터 일관성 및 정리 메커니즘

### 8.1 자동 정리 (TTL 기반)
- **온라인 상태**: 60초 TTL로 자동 만료
- **매치 데이터**: 300초 TTL로 자동 만료
- **전역 락**: 10초 TTL로 데드락 방지

### 8.2 수동 정리 (연결 해제 시)
1. 온라인 상태 해제
2. 대기열에서 제거
3. 활성 매치 정리
4. 상대방 대기열 재진입
5. 매칭된 방 삭제

### 8.3 데이터베이스 vs Redis 사용 기준
| 데이터 유형 | 저장소 | 이유 |
|-------------|--------|------|
| 사용자 정보, 매칭 설정 | PostgreSQL | 영구 저장 필요 |
| 매칭된 방 기록 | PostgreSQL | 영구 기록 필요 |
| 매칭 히스토리 | PostgreSQL | 통계 및 분석 |
| 대기열, 온라인 상태 | Redis | 고속 처리, 임시 데이터 |
| 매치 요청 | Redis | 실시간 처리, 자동 만료 |

---

## 9. 성능 고려사항

### 9.1 인덱스 권장사항
- `MatchSetting.user`: 자동 생성 (OneToOneField)
- `MatchHistory.user1, user2`: 복합 인덱스
- `MatchedRoom.user1, user2`: 복합 인덱스

### 9.2 쿼리 최적화
```python
# select_related 사용으로 N+1 쿼리 방지
MatchSetting.objects.select_related('user').get(user=user)

# 원자적 트랜잭션으로 동시성 문제 해결
with transaction.atomic():
    room = MatchedRoom.objects.create(user1=user1, user2=user2)
```

### 9.3 Redis 메모리 관리
- TTL 설정으로 자동 정리
- 주기적 오프라인 사용자 정리
- 적절한 데이터 구조 선택 (Sorted Set, JSON String)

---

이 명세서는 실제 구현된 코드를 기반으로 작성되었으며, Django ORM과 Redis를 혼합 사용하는 하이브리드 아키텍처를 반영합니다.