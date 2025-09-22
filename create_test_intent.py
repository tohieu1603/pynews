#!/usr/bin/env python
"""
Script để tạo test intent với order_code cụ thể để test callback
"""
import os
import sys
import django
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth.models import User
from apps.seapay.models import (
    PayPaymentIntent, PayPaymentAttempt, PayWallet, 
    IntentPurpose, PaymentStatus
)
from apps.seapay.services.wallet_topup_service import WalletTopupService

def create_test_intent():
    """Tạo test intent với order_code từ callback"""
    
    # Tìm hoặc tạo user test
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Created test user: {user.username}")
    else:
        print(f"✅ Using existing user: {user.username}")
    
    # Tạo hoặc lấy wallet
    wallet, created = PayWallet.objects.get_or_create(
        user=user,
        defaults={
            'balance': Decimal('0.00'),
            'currency': 'VND',
            'status': 'active'
        }
    )
    
    if created:
        print(f"✅ Created wallet: {wallet.wallet_id}")
    else:
        print(f"✅ Using existing wallet: {wallet.wallet_id}")
    
    # Tạo intent với order_code cụ thể từ callback
    order_code = "TOPUP175851230913D20160"
    amount = Decimal('10000')  # Từ callback data
    
    # Kiểm tra xem intent đã tồn tại chưa
    existing_intent = PayPaymentIntent.objects.filter(order_code=order_code).first()
    if existing_intent:
        print(f"✅ Intent already exists: {existing_intent.intent_id}")
        return existing_intent
    
    # Tạo intent mới
    intent = PayPaymentIntent.objects.create(
        user=user,
        amount=amount,
        currency='VND',
        purpose=IntentPurpose.WALLET_TOPUP,
        order_code=order_code,
        status=PaymentStatus.REQUIRES_PAYMENT_METHOD,
        expires_at=timezone.now() + timedelta(hours=1),
        metadata={
            'test_intent': True,
            'created_for_callback_test': True
        }
    )
    
    print(f"✅ Created payment intent: {intent.intent_id}")
    print(f"   Order code: {intent.order_code}")
    print(f"   Amount: {intent.amount}")
    print(f"   Status: {intent.status}")
    
    # Tạo attempt để hoàn thiện flow
    attempt = PayPaymentAttempt.objects.create(
        intent=intent,
        attempt_number=1,
        bank_code='BIDV',
        account_number='96247CISI1',
        account_name='BIDV Account',
        transfer_content=order_code,
        qr_image_url=f'https://qr.sepay.vn/img?acc=96247CISI1&bank=BIDV&amount={int(amount)}&des={order_code}&template=compact',
        status=PaymentStatus.REQUIRES_PAYMENT_METHOD
    )
    
    print(f"✅ Created payment attempt: {attempt.attempt_id}")
    print(f"   QR URL: {attempt.qr_image_url}")
    
    return intent

if __name__ == "__main__":
    try:
        intent = create_test_intent()
        print("\n🎉 Test intent created successfully!")
        print("Now you can test the callback again and it should work.")
        
    except Exception as e:
        print(f"❌ Error creating test intent: {e}")
        import traceback
        traceback.print_exc()