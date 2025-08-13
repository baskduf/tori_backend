# 실시간 음성 채팅 매칭 시스템 완전 명세

## 1. 시스템 개요

Django Channels와 WebRTC를 활용한 실시간 1:1 음성 채팅 매칭 시스템입니다. 사용자의 설정(나이, 성별 선호도)을 기반으로 적합한 상대를 찾아 실시간 음성 통화 세션을 제공합니다.

## 2. 아키텍처 구성

### 2.1 기술 스택
- **Backend**: Django + Django Channels (WebSocket)
- **Cache**: Redis (매칭 큐, 온라인 상태 관리)
- **Database**: Django ORM (PostgreSQL/MySQL 권장)
- **Frontend**: WebRTC (음성 통화)

### 2.2 주요 구성요소
- **MatchService**: 핵심 매칭 로직 처리
- **MatchConsumer**: WebSocket 연결 및 실시간 통신
- **VoiceChatSignalingConsumer**: WebRTC 시그널링 처리
- **Models**: 사용자 설정, 매치 히스토리, 방 관리

## 3. 데이터 모델

### 3.1 MatchSetting (매칭 설정)
```python
class MatchSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age_min = models.PositiveIntegerField(default=18)        # 선호 최소 나이
    age_max = models.PositiveIntegerField(default=99)        # 선호 최대 나이
    radius_km = models.PositiveIntegerField(default=1)       # 거리 반경 (현재 미사용)
    preferred_gender = models.CharField(                     # 선호 성별
        max_length=10,
        choices=[('male','Male'), ('female','Female'), ('any','Any')],
        default='any'
    )
```

### 3.2 MatchedRoom (매칭된 방)
```python
class MatchedRoom(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matched_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matched_user2')
    matched_at = models.DateTimeField(auto_now_add=True)
```

### 3.3 MatchHistory (매칭 히스토리)
```python
class MatchHistory(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_histories_1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_histories_2')
    matched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = (('user1', 'user2'),)
```

### 3.4 MatchQueue (매칭 큐 - 현재 미사용, Redis로 대체)
```python
class MatchQueue(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    entered_at = models.DateTimeField(auto_now_add=True)
```

### 3.5 MatchRequest (매치 요청 - 현재 미사용, Redis로 대체)
```python
class MatchRequest(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='from_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='to_requests')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'), 
            ('rejected', 'Rejected'),
            ('matched', 'Matched')
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
```

## 4. Redis 데이터 구조

### 4.1 키 정의
- `user_online:{user_id}`: 사용자 온라인 상태 (TTL: 60초)
- `match_queue`: 매칭 대기열 (Sorted Set, 타임스탬프로 정렬)
- `match_requests:{match_id}`: 매치 데이터 (JSON, TTL: 300초)
- `user_matches:{user_id}`: 사용자의 현재 매치 ID (TTL: 300초)
- `global_match_lock`: 전역 매칭 락 (TTL: 10초)

### 4.2 매치 데이터 구조
```json
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
    "user2_response": null
}
```

## 5. 매칭 시스템 플로우

### 5.1 사용자 연결 플로우
```
1. WebSocket 연결 → MatchConsumer.connect()
2. 채널 그룹 추가 (user_{user_id})
3. 온라인 상태 표시 (Redis)
4. Heartbeat 태스크 시작 (5초 주기)
```

### 5.2 매칭 요청 플로우
```
1. 클라이언트: {"action": "join_queue"}
2. 대기열 추가 (Redis Sorted Set)
3. 원자적 매칭 시도 (전역 락 사용)
4. 적합한 상대 검색
5. 매치 생성 또는 대기 상태 유지
```

### 5.3 원자적 매칭 알고리즘
```
1. 전역 락 획득 (global_match_lock)
2. 내 설정 조회
3. 이미 매칭 중인지 확인
4. 대기열에서 호환 가능한 상대 검색:
   - 온라인 상태 확인
   - 나이 범위 호환성 체크
   - 성별 선호도 호환성 체크
5. 매치 생성 및 양쪽 대기열에서 제거
6. 전역 락 해제
```

### 5.4 매치 응답 플로우
```
1. 매치 발견 → 양쪽에 "match_found" 전송
2. 사용자 응답 대기 (accept/reject)
3. 응답 처리:
   - 내가 accept, 상대 미응답 → "waiting_for_partner" 
   - 양쪽 모두 accept → 방 생성 → "match_success" 전송
   - 한쪽이라도 reject → 매치 정리 → 양쪽 다시 대기열 추가
4. 특별 케이스:
   - 상대방 오프라인 → "match_cancelled" 전송
   - 매치 만료 → 자동 정리 (TTL)
```

## 6. WebSocket API 명세

### 6.1 클라이언트 → 서버 메시지

#### 6.1.1 큐 참가
```json
{
    "action": "join_queue"
}
```

#### 6.1.2 매치 응답
```json
{
    "action": "respond",
    "partner": "상대방_사용자명",
    "response": "accept" | "reject"
}
```

#### 6.1.3 큐 떠나기
```json
{
    "action": "leave_queue"
}
```

### 6.2 서버 → 클라이언트 메시지

#### 6.2.1 매치 발견
```json
{
    "type": "match_found",
    "partner": "상대방_사용자명"
}
```

#### 6.2.2 매치 응답 결과
```json
{
    "type": "match_response",
    "result": "accept" | "reject",
    "from": "응답한_사용자명"
}
```

#### 6.2.3 매치 성공 (방 생성)
```json
{
    "type": "match_success",
    "room": "123_456"  // 방 이름
}
```

#### 6.2.4 매치 취소
```json
{
    "type": "match_cancelled",
    "from": "상대방_사용자명"
}
```

## 7. WebRTC 음성 통화

### 7.1 시그널링 서버 (VoiceChatSignalingConsumer)
- WebSocket 기반 시그널링
- 방 단위 그룹 관리 (`voicechat_{room_name}`)
- SDP Offer/Answer, ICE Candidate 중계

### 7.2 시그널링 메시지 타입
- `offer`: WebRTC Offer SDP
- `answer`: WebRTC Answer SDP  
- `ice-candidate`: ICE Candidate 정보

## 8. 호환성 확인 로직

### 8.1 나이 호환성
```python
def check_age_compatibility(my_setting, other_setting):
    # 내가 상대방 나이를 수용하는가
    if not (my_setting['age_min'] <= other_setting['user_age'] <= my_setting['age_max']):
        return False
    # 상대방이 내 나이를 수용하는가  
    if not (other_setting['age_min'] <= my_setting['user_age'] <= other_setting['age_max']):
        return False
    return True
```

### 8.2 성별 호환성
```python
def check_gender_compatibility(my_setting, other_setting):
    # 내 성별 선호도 확인
    if (my_setting['preferred_gender'] != 'any' and 
        other_setting['user_gender'] != my_setting['preferred_gender']):
        return False
    # 상대방 성별 선호도 확인
    if (other_setting['preferred_gender'] != 'any' and 
        my_setting['user_gender'] != other_setting['preferred_gender']):
        return False
    return True
```

## 9. 에러 처리 및 정리

### 9.1 연결 해제 시 정리
```
1. 온라인 상태 해제
2. 대기열에서 제거
3. 활성 매치 정리
4. 상대방 다시 대기열 추가
5. 매칭된 방 정리
6. 영향받은 사용자들에게 알림
```

### 9.2 오프라인 사용자 정리
- 주기적으로 대기열의 오프라인 사용자 제거
- 매치 데이터 TTL로 자동 만료
- 온라인 상태 TTL로 자동 해제

## 10. 보안 및 성능 고려사항

### 10.1 동시성 제어
- 전역 매칭 락으로 race condition 방지
- 원자적 매치 생성 보장
- Redis를 통한 분산 락 구현

### 10.2 성능 최적화
- Redis 캐시 활용으로 빠른 응답
- 비동기 처리로 높은 동시성 지원
- 효율적인 대기열 관리 (Sorted Set)

### 10.3 보안
- 사용자 인증 확인 (is_anonymous 체크)
- 매치 데이터 TTL로 자동 정리
- 온라인 상태 heartbeat 검증

## 11. 확장 가능성

### 11.1 추가 기능
- 거리 기반 매칭 (GPS 좌표)
- 관심사 기반 매칭
- 매치 히스토리 관리
- 평점 시스템
- 신고 기능

### 11.2 성능 확장
- 다중 Redis 인스턴스 (샤딩)
- 로드 밸런서를 통한 수평 확장
- 매칭 서버 분리 (마이크로서비스)

## 12. 배포 및 운영

### 12.1 필수 설정
```python
# settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
    },
}

# 캐시 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 12.2 모니터링
- Redis 메모리 사용량 모니터링
- WebSocket 연결 수 모니터링  
- 매칭 성공률 추적
- 응답 시간 모니터링

## 13. 주요 구현 이슈 및 해결책

### 13.1 Redis 클라이언트 접근
```python
# Django 캐시를 통한 Redis 클라이언트 접근
redis_client = cache.client.get_client()
redis_client.zadd(self.queue_key, {self.user_id: time.time()})
```

### 13.2 JSON 직렬화/역직렬화 처리
```python
# 매치 데이터 저장 시
cache.set(match_data_key, json.dumps(match_data), timeout=self.MATCH_TTL)

# 매치 데이터 조회 시
match_data_str = cache.get(match_data_key)
if match_data_str:
    try:
        match_data = json.loads(match_data_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        # 에러 처리 로직
```

### 13.3 동기/비동기 혼합 처리
```python
# Django ORM을 비동기 컨텍스트에서 사용
user = await database_sync_to_async(User.objects.get)(id=int(user_id))

# 복잡한 쿼리의 경우
def _fetch_setting():
    return MatchSetting.objects.select_related('user').get(user=other_user)
    
other_setting_obj = await database_sync_to_async(_fetch_setting)()
```

### 13.4 타입 일치성 보장
```python
# Redis에서 가져온 바이트를 문자열로 변환
user_id = user_id_bytes.decode('utf-8')

# 숫자 ID를 문자열로 통일
user_id_str = str(self.user_id)
```

## 14. 실제 코드에서 발견된 특이사항

### 14.1 매치 ID 생성 방식
```python
# 작은 ID를 먼저, 큰 ID를 나중에 배치
match_id = f"{min(self.user_id, str(partner.id))}:{max(self.user_id, str(partner.id))}"
```

### 14.2 프론트엔드 호환성 고려
- 에러 응답을 최소화 (조용한 실패 처리)
- 기존 프론트엔드와 호환되는 메시지 형식 유지
- 로깅은 상세히 하되, 클라이언트에는 필수 정보만 전송

### 14.3 메모리 효율성
- TTL 기반 자동 정리로 메모리 누수 방지
- 불필요한 데이터 구조 제거 (MatchQueue, MatchRequest 모델은 정의되어 있으나 실제로는 Redis 사용)