def get_redis_settings():
    #REDIS_PASSWORD = "23s25fgh"
    #REDIS_HOST = "34.46.53.163"  # VM 외부 IP
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 1  # 필요시 DB 번호 지정

    # Django CACHES 설정
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            #'LOCATION': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1',
            'LOCATION': f'redis://:@{REDIS_HOST}:{REDIS_PORT}/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 100,
                    'retry_on_timeout': True,
                    'decode_responses': False
                },
            }
        }
    }

    # 매칭 관련 TTL 설정
    REDIS_MATCH_CONFIG = {
        'ONLINE_TTL': 30,
        'PROCESSING_TTL': 10,
        'QUEUE_TTL': 300,
        'MATCH_TTL': 600,
    }

    CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            #"hosts": [f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"]
            "hosts": [f"redis://:@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"]
        },
    },
    }

    return CACHES, CHANNEL_LAYERS
