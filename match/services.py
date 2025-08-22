import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from channels.db import database_sync_to_async
from .models import MatchSetting, MatchedRoom
from gem.models import UserGemWallet


from typing import Tuple, Optional            # 타입 힌트
from asgiref.sync import sync_to_async      # atomic 트랜잭션

User = get_user_model()
logger = logging.getLogger(__name__)

class MatchService:
    def __init__(self, user):
        self.user = user
        self.user_id = str(user.id)
        
        # Redis 키 정의 (기존 호환성 유지)
        self.user_online_key = f"user_online:{self.user_id}"
        self.queue_key = "match_queue"  # Sorted Set: 매칭 대기열
        self.match_requests_key = "match_requests"  # 매치 데이터 키 프리픽스
        self.user_matches_key = f"user_matches:{self.user_id}"  # 유저의 현재 매치
        
        # Lock 키들
        self.global_match_lock = "global_match_lock"
        self.user_lock_key = f"user_lock:{self.user_id}"
        
        # TTL 상수
        self.ONLINE_TTL = 60
        self.MATCH_TTL = 300  # 5분
        self.LOCK_TTL = 10

    # ---------------------------
    # 기본 상태 관리 (기존 메서드명 유지)
    # ---------------------------
    async def mark_user_online(self) -> bool:
        """사용자 온라인 상태 표시"""
        try:
            cache.set(self.user_online_key, True, timeout=self.ONLINE_TTL)
            return True
        except Exception as e:
            logger.error(f"Error marking user {self.user_id} online: {e}")
            return False

    async def mark_user_offline(self):
        """사용자 오프라인 처리"""
        try:
            cache.delete(self.user_online_key)
            await self.handle_disconnect_cleanup()
        except Exception as e:
            logger.error(f"Error marking user {self.user_id} offline: {e}")

    async def is_user_online(self, user_id: str = None) -> bool:
        """온라인 상태 확인"""
        target_id = user_id or self.user_id
        try:
            return bool(cache.get(f"user_online:{str(target_id)}"))
        except Exception:
            return False

    # ---------------------------
    # 큐 관리 (기존 메서드명 유지)
    # ---------------------------
    async def add_to_queue(self) -> bool:
        """매칭 대기열에 추가"""
        try:
            # 이미 매칭 중인지 확인
            if await self._has_active_match():
                logger.info(f"User {self.user_id} already has active match")
                return False
            
            # 온라인 상태 갱신
            await self.mark_user_online()
            
            # 큐에 추가 (타임스탬프로 정렬)
            redis_client = cache.client.get_client()
            redis_client.zadd(self.queue_key, {self.user_id: time.time()})
            
            logger.info(f"User {self.user_id} added to queue")
            return True
        except Exception as e:
            logger.error(f"Error adding user {self.user_id} to queue: {e}")
            return False

    async def remove_from_queue(self) -> bool:
        """대기열에서 제거"""
        try:
            redis_client = cache.client.get_client()
            redis_client.zrem(self.queue_key, self.user_id)
            logger.info(f"User {self.user_id} removed from queue")
            return True
        except Exception as e:
            logger.error(f"Error removing user {self.user_id} from queue: {e}")
            return False

    # ---------------------------
    # 설정 조회 (기존 메서드명 유지)
    # ---------------------------
    async def get_my_setting(self) -> Optional[Dict[str, Any]]:
        """사용자 매칭 설정 조회"""
        try:
            def _fetch():
                return MatchSetting.objects.select_related('user').filter(user=self.user).first()
            
            setting = await database_sync_to_async(_fetch)()
            if not setting:
                return None
                
            return {
                'age_min': setting.age_min,
                'age_max': setting.age_max,
                'preferred_gender': setting.preferred_gender,
                'user_age': setting.user.age,
                'user_gender': setting.user.gender
            }
        except Exception as e:
            logger.error(f"Error getting settings for user {self.user_id}: {e}")
            return None

    # ---------------------------
    # 핵심: 원자적 매칭 로직
    # ---------------------------


    async def find_and_match_atomic(self) -> Tuple[str, Optional[Any]]:
        """전역 락을 사용한 원자적 매칭 + 보석 차감 (상대 발견 후 차감)"""
        if not cache.set(self.global_match_lock, self.user_id, timeout=self.LOCK_TTL, nx=True):
            return ("matching_in_progress", None)
        
        try:
            # 1. 내 설정 조회
            my_setting = await self.get_my_setting()
            if not my_setting:
                return ("no_setting", None)

            # 2. 이미 매칭 중인지 확인
            if await self._has_active_match():
                return ("already_matched", None)

            # 3. 적합한 상대 찾기
            partner = await self._find_compatible_partner(my_setting)
            if not partner:
                return ("no_match", None)

            # 4. 상대를 찾았으니 보석 차감
            try:
                wallet = await sync_to_async(
                    UserGemWallet.objects.select_for_update().get
                )(user_id=self.user_id)
            except Exception:  # ObjectDoesNotExist 대신 일반 Exception
                # 지갑 없으면 새로 생성
                def create_wallet():
                    return UserGemWallet.objects.create(user_id=self.user_id, balance=0)
                wallet = await sync_to_async(create_wallet)()

            deduct_amount = 0
            preferred_gender = my_setting.get('preferred_gender', '').lower()
            if preferred_gender == 'female':
                deduct_amount = 30
            elif preferred_gender == 'male':
                deduct_amount = 5
            elif preferred_gender == 'any':
                deduct_amount = 0

            if wallet.balance < deduct_amount:
                return ("not_enough_gems", None)

            def deduct_gems():
                with transaction.atomic():
                    wallet.refresh_from_db()
                    if wallet.balance < deduct_amount:
                        raise ValueError("Not enough gems")
                    wallet.balance -= deduct_amount
                    wallet.save(update_fields=["balance", "updated_at"])
            await sync_to_async(deduct_gems)()

            # 5. 매치 생성
            match_id = await self._create_match(partner)
            if not match_id:
                return ("match_creation_failed", None)

            # 6. 양쪽 큐에서 제거
            await self.remove_from_queue()
            partner_service = MatchService(partner)
            await partner_service.remove_from_queue()

            logger.info(f"Match created: {self.user_id} <-> {partner.id}")
            return ("match_created", partner)

        except ValueError:
            return ("not_enough_gems", None)
        except Exception as e:
            logger.error(f"Error in atomic matching: {e}")
            return ("error", None)
        finally:
            cache.delete(self.global_match_lock)



    async def _find_compatible_partner(self, my_setting: Dict[str, Any]) -> Optional[User]:
        """호환 가능한 파트너 찾기"""
        try:
            redis_client = cache.client.get_client()
            queue_users = redis_client.zrange(self.queue_key, 0, -1)
            
            for user_id_bytes in queue_users:
                other_user_id = user_id_bytes.decode('utf-8')
                
                # 자신 제외
                if other_user_id == self.user_id:
                    continue
                
                # 온라인 상태 확인
                if not await self.is_user_online(other_user_id):
                    # 오프라인 사용자는 큐에서 제거
                    redis_client.zrem(self.queue_key, other_user_id)
                    continue
                
                # 이미 매칭 중인지 확인
                if cache.get(f"user_matches:{str(other_user_id)}"):
                    continue
                
                # 사용자 정보 조회
                try:
                    other_user = await database_sync_to_async(User.objects.get)(id=int(other_user_id))
                except User.DoesNotExist:
                    redis_client.zrem(self.queue_key, other_user_id)
                    continue
                
                # 상대방 설정 조회
                try:
                    def _fetch_other_setting():
                        return MatchSetting.objects.select_related('user').get(user=other_user)
                    other_setting_obj = await database_sync_to_async(_fetch_other_setting)()
                except MatchSetting.DoesNotExist:
                    continue
                
                other_setting = {
                    'age_min': other_setting_obj.age_min,
                    'age_max': other_setting_obj.age_max,
                    'preferred_gender': other_setting_obj.preferred_gender,
                    'user_age': other_setting_obj.user.age,
                    'user_gender': other_setting_obj.user.gender
                }
                
                # 호환성 확인
                if self._is_compatible(my_setting, other_setting):
                    return other_user
                    
            return None
        except Exception as e:
            logger.error(f"Error finding compatible partner: {e}")
            return None

    def _is_compatible(self, my_setting: Dict[str, Any], other_setting: Dict[str, Any]) -> bool:
        """매칭 호환성 확인"""
        try:
            # 필수 정보 확인
            for key in ('user_age', 'user_gender', 'age_min', 'age_max', 'preferred_gender'):
                if my_setting.get(key) is None or other_setting.get(key) is None:
                    return False

            # 나이 범위 확인
            if not (my_setting['age_min'] <= other_setting['user_age'] <= my_setting['age_max']):
                return False
            if not (other_setting['age_min'] <= my_setting['user_age'] <= other_setting['age_max']):
                return False

            # 성별 선호도 확인
            if (my_setting['preferred_gender'] != 'any' and 
                other_setting['user_gender'] != my_setting['preferred_gender']):
                return False
            if (other_setting['preferred_gender'] != 'any' and 
                my_setting['user_gender'] != other_setting['preferred_gender']):
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking compatibility: {e}")
            return False

    async def _create_match(self, partner: User) -> Optional[str]:
        """매치 생성"""
        try:
            match_id = f"{min(self.user_id, str(partner.id))}:{max(self.user_id, str(partner.id))}"
            logger.info(f"Creating match with match_id: {match_id} for users {self.user_id} and {partner.id}")
            
            match_data = {
                'match_id': str(match_id),
                'user1': str(self.user_id),
                'user2': str(partner.id),
                'user1_name': self.user.username,
                'user2_name': partner.username,
                'status': 'pending',
                'created_at': time.time(),
                'user1_response': None,
                'user2_response': None
            }
            
            # Django 캐시 인터페이스 사용 (timeout 파라미터 사용)
            cache.set(self.match_requests_key + ":" + match_id, json.dumps(match_data), timeout=self.MATCH_TTL)
            
            # 각 유저에게 매치 ID 할당 (timeout 사용)
            cache.set(f"user_matches:{str(self.user_id)}", str(match_id), timeout=self.MATCH_TTL)
            cache.set(f"user_matches:{str(partner.id)}", str(match_id), timeout=self.MATCH_TTL)
            
            logger.info(f"Match created successfully: {match_id}")
            return str(match_id)
            
        except Exception as e:
            logger.error(f"Error creating match: {e}", exc_info=True)
            return None

    async def get_current_match_requests(self) -> List[Dict]:
        logger.info(f"User {self.user_id} get_current_match_requests called")
        try:
            match_id = cache.get(f"user_matches:{str(self.user_id)}")
            logger.info(f"User {self.user_id} cache user_matches: {match_id}")
            
            if not match_id:
                return []
            
            # 매치 생성과 동일한 방식으로 데이터 조회 (Django 캐시 사용)
            match_data_key = self.match_requests_key + ":" + match_id
            match_data_str = cache.get(match_data_key)
            logger.info(f"User {self.user_id} cache match_data key: {match_data_key}, data: {match_data_str}")
            
            if not match_data_str:
                # 매치 데이터가 없으면 user_matches도 정리
                cache.delete(f"user_matches:{str(self.user_id)}")
                logger.warning(f"Match data not found for key: {match_data_key}, cleaned up user_matches")
                return []
            
            # JSON 파싱
            try:
                match_data = json.loads(match_data_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for match_id {match_id}: {e}")
                cache.delete(f"user_matches:{str(self.user_id)}")
                return []
                
            logger.info(f"User {self.user_id} match_data decoded: {match_data}")

            # 타입 일치를 위해 문자열로 변환하여 비교
            user_id_str = str(self.user_id)
            my_response_key = 'user1_response' if match_data['user1'] == user_id_str else 'user2_response'
            logger.info(f"User {self.user_id} my_response_key: {my_response_key}, value: {match_data[my_response_key]}")

            # 아직 응답하지 않은 매치만 반환
            if match_data[my_response_key] is None:
                try:
                    user1 = await database_sync_to_async(User.objects.get)(id=int(match_data['user1']))
                    user2 = await database_sync_to_async(User.objects.get)(id=int(match_data['user2']))
                    
                    return [{
                        **match_data,
                        "from_username": user1.username,
                        "to_username": user2.username
                    }]
                except User.DoesNotExist as e:
                    logger.error(f"User not found for match {match_id}: {e}")
                    # 사용자가 존재하지 않으면 매치 정리
                    await self._cleanup_match(match_id, match_data['user1'], match_data['user2'])
                    return []
                    
            return []
            
        except Exception as e:
            logger.error(f"Error getting current match requests for user {self.user_id}: {e}", exc_info=True)
            return []

    # ---------------------------
    # 헬퍼 메서드들
    # ---------------------------
    async def _has_active_match(self) -> bool:
        """활성 매치가 있는지 확인"""
        try:
            match_id = cache.get(f"user_matches:{str(self.user_id)}")
            return match_id is not None
        except Exception:
            return False

    async def _cleanup_match(self, match_id: str, user1_id: str = None, user2_id: str = None):
        """매치 정리 - Django 캐시 버전"""
        try:
            # 사용자 ID가 제공되지 않은 경우 매치 데이터에서 추출
            if not user1_id or not user2_id:
                match_data_key = self.match_requests_key + ":" + match_id
                match_data_str = cache.get(match_data_key)
                if match_data_str:
                    try:
                        match_data = json.loads(match_data_str)
                        user1_id = match_data['user1']
                        user2_id = match_data['user2']
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse match data for cleanup: {match_id}")
            
            # 정리
            match_data_key = self.match_requests_key + ":" + match_id
            cache.delete(match_data_key)
            
            if user1_id:
                cache.delete(f"user_matches:{user1_id}")
            if user2_id:
                cache.delete(f"user_matches:{user2_id}")
                
            logger.info(f"Cleaned up match: {match_id} (users: {user1_id}, {user2_id})")
            
        except Exception as e:
            logger.error(f"Error cleaning up match {match_id}: {e}")

    async def _create_matched_room_atomic(self, user1: User, user2: User):
        """원자적 방 생성"""
        try:
            def create_room():
                with transaction.atomic():
                    existing_room = MatchedRoom.objects.filter(
                        Q(user1=user1, user2=user2) | Q(user1=user2, user2=user1)
                    ).first()
                    
                    if existing_room:
                        return existing_room
                    
                    room = MatchedRoom.objects.create(
                        user1=min(user1, user2, key=lambda u: u.id),
                        user2=max(user1, user2, key=lambda u: u.id)
                    )
                    return room
                    
            return await database_sync_to_async(create_room)()
        except Exception as e:
            logger.error(f"Error creating matched room: {e}")
            return None

    # ---------------------------
    # 연결 해제 처리 (기존 메서드명 유지)
    # ---------------------------
    async def handle_disconnect_cleanup(self) -> List[int]:
        """연결 해제 시 정리"""
        affected_users = []
        try:
            # 온라인 상태 해제
            cache.delete(self.user_online_key)
            
            # 큐에서 제거
            await self.remove_from_queue()
            
            # 활성 매치 처리
            match_id = cache.get(f"user_matches:{str(self.user_id)}")
            if match_id:
                # Django 캐시에서 매치 데이터 조회 (새로운 구조에 맞게)
                match_data_key = self.match_requests_key + ":" + match_id
                match_data_str = cache.get(match_data_key)
                
                if match_data_str:
                    try:
                        match_data = json.loads(match_data_str)
                        user_id_str = str(self.user_id)
                        other_user_id = match_data['user2'] if match_data['user1'] == user_id_str else match_data['user1']
                        
                        # 상대방을 다시 큐에 추가
                        if await self.is_user_online(other_user_id):
                            try:
                                other_user = await database_sync_to_async(User.objects.get)(id=int(other_user_id))
                                other_service = MatchService(other_user)
                                await other_service.add_to_queue()
                                affected_users.append(int(other_user_id))
                                logger.info(f"Re-added user {other_user_id} to queue after partner disconnect")
                            except User.DoesNotExist:
                                logger.warning(f"Other user {other_user_id} not found during cleanup")
                                pass
                        
                        # 매치 정리
                        await self._cleanup_match(match_id, match_data['user1'], match_data['user2'])
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse match data during disconnect cleanup: {e}")
                        # JSON 파싱 실패해도 기본 정리는 수행
                        await self._cleanup_match(match_id)
            
            # 매칭된 방들 정리
            room_partners = await self.get_matched_rooms_and_delete()
            for partner_id in room_partners:
                if await self.is_user_online(partner_id):
                    try:
                        partner_user = await database_sync_to_async(User.objects.get)(id=partner_id)
                        partner_service = MatchService(partner_user)
                        await partner_service.add_to_queue()
                        affected_users.append(partner_id)
                        logger.info(f"Re-added matched room partner {partner_id} to queue after disconnect")
                    except User.DoesNotExist:
                        logger.warning(f"Partner user {partner_id} not found during cleanup")

            affected_users.append(self.user.id)
            logger.info(f"Disconnect cleanup completed for user {self.user_id}, affected users: {affected_users}")
            return list(set(affected_users))
            
        except Exception as e:
            logger.error(f"Error in disconnect cleanup for user {self.user_id}: {e}", exc_info=True)
            return []

    async def get_matched_rooms_and_delete(self) -> List[int]:
        """매칭된 방들 조회 및 삭제"""
        try:
            def get_and_delete_rooms():
                with transaction.atomic():
                    rooms = MatchedRoom.objects.select_for_update().filter(
                        Q(user1=self.user) | Q(user2=self.user)
                    ).select_related('user1', 'user2')

                    partners = []
                    room_ids = []
                    for room in rooms:
                        partner = room.user2 if room.user1 == self.user else room.user1
                        partners.append(partner.id)
                        room_ids.append(room.id)

                    if room_ids:
                        MatchedRoom.objects.filter(id__in=room_ids).delete()
                    return partners
                    
            return await database_sync_to_async(get_and_delete_rooms)()
        except Exception as e:
            logger.error(f"Error in get_matched_rooms_and_delete: {e}")
            return []

    # ---------------------------
    # 모니터링 및 정리 (수정된 부분들)
    # ---------------------------
    async def get_queue_status(self) -> Dict[str, Any]:
        """큐 상태 조회"""
        try:
            redis_client = cache.client.get_client()
            queue_count = redis_client.zcard(self.queue_key)
            
            # 매치 수 계산 (Django 캐시 구조에 맞게 수정)
            # Hash 구조가 아니므로 직접 계산하기 어려움 - 큐 사용자 기반으로 추정
            active_matches = 0
            
            queue_users = []
            user_ids = redis_client.zrange(self.queue_key, 0, -1)
            for user_id_bytes in user_ids:
                user_id = user_id_bytes.decode('utf-8')
                online_status = await self.is_user_online(user_id)
                # 수정: 각 사용자의 매치 상태 확인 (기존 버그 수정)
                has_match = bool(cache.get(f"user_matches:{user_id}"))
                if has_match:
                    active_matches += 1
                    
                queue_users.append({
                    'user_id': user_id,
                    'online': online_status,
                    'has_match': has_match
                })
            
            # 매치는 2명씩이므로 2로 나누기 (중복 카운트 보정)
            estimated_matches = active_matches // 2
            
            return {
                'queue_count': queue_count,
                'estimated_match_count': estimated_matches,
                'active_match_users': active_matches,
                'queue_users': queue_users
            }
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {}

    async def cleanup_offline_users_from_queue(self) -> int:
        """오프라인 사용자들 정리"""
        try:
            redis_client = cache.client.get_client()
            queue_users = redis_client.zrange(self.queue_key, 0, -1)
            cleaned_count = 0
            
            for user_id_bytes in queue_users:
                user_id = user_id_bytes.decode('utf-8')
                if not await self.is_user_online(user_id):
                    redis_client.zrem(self.queue_key, user_id)
                    cache.delete(f"user_matches:{user_id}")
                    cleaned_count += 1
                    logger.info(f"Cleaned offline user {user_id} from queue")
            
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning offline users: {e}")
            return 0

    async def get_user_status(self) -> Dict[str, Any]:
        """사용자 상태 조회"""
        try:
            redis_client = cache.client.get_client()
            return {
                'user_id': self.user_id,
                'online': await self.is_user_online(),
                'in_queue': redis_client.zscore(self.queue_key, self.user_id) is not None,
                'has_active_match': await self._has_active_match(),
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Error getting user status: {e}")
            return {'error': str(e)}
        

    # ---------------------------
    # 매치 응답 처리
    # ---------------------------
    async def update_match_status_and_create_room(self, match_data: Dict, response: str) -> Tuple[str, Optional[User]]:
        """매치 응답 처리 및 방 생성"""
        try:
            logger.info(f"Received response: {response} (type: {type(response)}) from user {self.user_id}")
            match_id = match_data['match_id']
            
            # Django 캐시에서 현재 매치 데이터 조회 (새로운 구조에 맞게)
            match_data_key = self.match_requests_key + ":" + match_id
            current_match_str = cache.get(match_data_key)
            if not current_match_str:
                cache.delete(f"user_matches:{str(self.user_id)}")
                return ("match_expired", None)
            
            try:
                current_match = json.loads(current_match_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for match {match_id}: {e}")
                await self._cleanup_match(match_id)
                return ("invalid_match_data", None)
            
            # 상대방 정보 확인
            user_id_str = str(self.user_id)
            other_user_id = current_match['user2'] if current_match['user1'] == user_id_str else current_match['user1']
            
            if not await self.is_user_online(other_user_id):
                await self._cleanup_match(match_id)
                return ("partner_offline", None)
            
            try:
                other_user = await database_sync_to_async(User.objects.get)(id=int(other_user_id))
            except User.DoesNotExist:
                await self._cleanup_match(match_id)
                return ("partner_not_found", None)
            
            # 응답 업데이트
            response_key = 'user1_response' if current_match['user1'] == user_id_str else 'user2_response'
            current_match[response_key] = response
            current_match['updated_at'] = time.time()
            
            if response == 'accept':
                # 양쪽 모두 수락했는지 확인
                other_response_key = 'user2_response' if current_match['user1'] == user_id_str else 'user1_response'
                
                if current_match[other_response_key] == 'accept':
                    # 둘 다 수락 -> 방 생성
                    room = await self._create_matched_room_atomic(self.user, other_user)
                    if room:
                        await self._cleanup_match(match_id, current_match['user1'], current_match['user2'])
                        logger.info(f"Room created successfully for users {self.user_id} and {other_user_id}")
                        return ("success", other_user)
                    else:
                        logger.error(f"Room creation failed for users {self.user_id} and {other_user_id}")
                        return ("room_creation_failed", None)
                else:
                    # 내가 수락, 상대방 대기 중 - Django 캐시로 업데이트
                    cache.set(match_data_key, json.dumps(current_match), timeout=self.MATCH_TTL)
                    logger.info(f"User {self.user_id} accepted, waiting for partner {other_user_id}")
                    return ("waiting_for_partner", None)
            else:
                logger.info(f"User {self.user_id} rejected match with {other_user_id}")
                # 거절 -> 매치 정리하고 다시 큐에 추가
                await self._cleanup_match(match_id, current_match['user1'], current_match['user2'])
                
                # 둘 다 다시 큐에 추가
                await self.add_to_queue()
                if await self.is_user_online(other_user_id):
                    other_service = MatchService(other_user)
                    await other_service.add_to_queue()
                    logger.info(f"Re-added both users to queue after rejection")
                
                return ("rejected", other_user)
                
        except Exception as e:
            logger.error(f"Error updating match status: {e}", exc_info=True)
            return ("error", None)