# ---------------------------
# Django Shell Script
# ---------------------------

# 1️⃣ 필요한 모델 임포트
from gem.models import UserGemWallet, GemTransaction
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# 2️⃣ 유저 선택 (이메일 기준)
user_email = 'baskduf@gmail.com'  # <-- 여기에 유저 이메일 입력
try:
    user = User.objects.get(email=user_email)
except User.DoesNotExist:
    print(f"No user found with email: {user_email}")
    raise

# 3️⃣ 지갑 조회 또는 생성
wallet, created = UserGemWallet.objects.get_or_create(user=user)

# 4️⃣ 젬 100 충전
grant_amount = 100
wallet.balance += grant_amount
wallet.updated_at = timezone.now()
wallet.save(update_fields=['balance', 'updated_at'])

# 5️⃣ 트랜잭션 기록
GemTransaction.objects.create(
    user=user,
    transaction_type='admin_grant',  # 'purchase', 'reward' 등 자유롭게 지정 가능
    amount=grant_amount,
    note='Admin granted 100 gems via shell'
)

print(f"{user.username} ({user.email}) now has {wallet.balance} gems.")
