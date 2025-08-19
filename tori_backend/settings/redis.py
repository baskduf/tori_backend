CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 100, 'retry_on_timeout': True, 'decode_responses': False},
        }
    }
}

REDIS_MATCH_CONFIG = {
    'ONLINE_TTL': 30,
    'PROCESSING_TTL': 10,
    'QUEUE_TTL': 300,
    'MATCH_TTL': 600,
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    },
}
