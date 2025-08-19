import os

ENVIRONMENT = os.getenv("DJANGO_ENV", "dev")  # dev / prod

if ENVIRONMENT == "prod":
    from .prod import *
else:
    from .dev import *

# OAuth 설정 통합
from .oauth import *
# Redis 설정 통합
from .redis import *
