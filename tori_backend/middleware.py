import logging
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        user = User.objects.get(id=user_id)
        logger.info(f"JWT authentication succeeded: user_id={user_id}, username={user.username}")
        return user
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
    except jwt.DecodeError:
        logger.warning("Failed to decode JWT token")
    except User.DoesNotExist:
        logger.warning(f"User not found for user_id from JWT payload: {payload.get('user_id')}")
    except Exception as e:
        logger.error(f"Unexpected error during JWT authentication: {e}")
    return AnonymousUser()

class JwtAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        logger.info(f"[JwtAuthMiddleware] Query string: {query_string}")

        query_params = parse_qs(query_string)
        token = query_params.get("token")
        if token:
            token = token[0]
            logger.info(f"[JwtAuthMiddleware] Token found: {token[:10]}...")  # Log token prefix only
            user = await get_user_from_token(token)
        else:
            logger.info("[JwtAuthMiddleware] No token found, assigning AnonymousUser")
            user = AnonymousUser()

        scope['user'] = user
        return await self.inner(scope, receive, send)
