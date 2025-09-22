"""
Demo script để test luồng nạp tiền ví hoàn chỉnh
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.seapay.services.wallet_topup_service import WalletTopupService
from apps.seapay.models import PayWallet, PayPaymentIntent, PayPayment, PayWalletLedger

User = get_user_model()


def demo_wallet_topup():
    """Demo luồng nạp tiền ví"""
    print("=== DEMO WALLET TOPUP FLOW ===\n")
    
    # Tạo hoặc lấy user test
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    print(f"User: {user.username} ({'created' if created else 'existing'})")
    
    # Initialize service
    topup_service = WalletTopupService()
    
    # Bước 1: Tạo intent
    print("\n--- Bước 1: Tạo Payment Intent ---")
    amount = Decimal('100000')  # 100k VND
    intent = topup_service.create_topup_intent(
        user=user,
        amount=amount,
        currency="VND",
        expires_in_minutes=60,
        metadata={'demo': True}
    )
    
    print(f"Intent ID: {intent.intent_id}")
    print(f"Order Code: {intent.order_code}")
    print(f"Amount: {intent.amount} VND")
    print(f"Status: {intent.status}")
    print(f"Expires at: {intent.expires_at}")
    
    # Bước 2: Tạo attempt với QR code
    print("\n--- Bước 2: Tạo Payment Attempt với QR Code ---")
    try:
        attempt = topup_service.create_payment_attempt(
            intent=intent,
            bank_code="VCB"
        )
        
        print(f"Attempt ID: {attempt.attempt_id}")
        print(f"Bank Code: {attempt.bank_code}")
        print(f"Account Number: {attempt.account_number}")
        print(f"Account Name: {attempt.account_name}")
        print(f"Transfer Content: {attempt.transfer_content}")
        print(f"Transfer Amount: {attempt.transfer_amount}")
        print(f"QR Image URL: {attempt.qr_image_url}")
        print(f"Status: {attempt.status}")
        
        # Cập nhật intent status
        intent.refresh_from_db()
        print(f"Intent Status Updated: {intent.status}")
        
    except Exception as e:
        print(f"Error creating attempt: {e}")
    
    # Bước 3: Simulate webhook từ SePay
    print("\n--- Bước 3: Simulate SePay Webhook ---")
    mock_webhook_payload = {
        'id': 123456789,  # sepay_tx_id
        'gateway': 'VCB',
        'transactionDate': '2025-09-22 10:30:00',
        'accountNumber': attempt.account_number or '1234567890',
        'subAccount': '',
        'code': 'IN',
        'content': intent.order_code,  # Match với order_code
        'transferType': 'bank_transfer',
        'description': f'Nap tien vi {intent.order_code}',
        'transferAmount': float(amount),
        'referenceCode': f'REF_{intent.order_code}',
        'accumulated': 0
    }
    
    try:
        webhook_result = topup_service.process_webhook_event(mock_webhook_payload)
        print(f"Webhook Result: {webhook_result}")
        
        # Check if payment was created
        if webhook_result.get('status') == 'success':
            payment_id = webhook_result.get('payment_id')
            if payment_id:
                payment = PayPayment.objects.get(payment_id=payment_id)
                print(f"Payment Created: {payment.payment_id}")
                print(f"Payment Status: {payment.status}")
                print(f"Provider Payment ID: {payment.provider_payment_id}")
        
    except Exception as e:
        print(f"Error processing webhook: {e}")
    
    # Bước 4: Check final status
    print("\n--- Bước 4: Final Status Check ---")
    try:
        status_data = topup_service.get_topup_status(str(intent.intent_id), user)
        
        print("Intent Status:")
        print(f"  ID: {status_data['intent']['id']}")
        print(f"  Status: {status_data['intent']['status']}")
        print(f"  Amount: {status_data['intent']['amount']}")
        
        if status_data.get('payment'):
            print("Payment Status:")
            print(f"  ID: {status_data['payment']['id']}")
            print(f"  Status: {status_data['payment']['status']}")
            print(f"  Provider ID: {status_data['payment']['provider_payment_id']}")
        
        if status_data.get('ledger'):
            print("Ledger Entry:")
            print(f"  ID: {status_data['ledger']['id']}")
            print(f"  Balance Before: {status_data['ledger']['balance_before']}")
            print(f"  Balance After: {status_data['ledger']['balance_after']}")
        
        # Check wallet balance
        wallet = PayWallet.objects.filter(user=user).first()
        if wallet:
            print(f"Current Wallet Balance: {wallet.balance} {wallet.currency}")
        
    except Exception as e:
        print(f"Error checking status: {e}")
    
    print("\n=== DEMO COMPLETED ===")


def cleanup_demo_data():
    """Cleanup demo data"""
    print("Cleaning up demo data...")
    
    try:
        user = User.objects.get(username='test_user')
        
        # Delete related data
        PayWalletLedger.objects.filter(wallet__user=user).delete()
        PayPayment.objects.filter(user=user).delete()
        PayPaymentIntent.objects.filter(user=user).delete()
        PayWallet.objects.filter(user=user).delete()
        
        # Delete user
        user.delete()
        
        print("Demo data cleaned up successfully")
        
    except User.DoesNotExist:
        print("No demo data to clean up")
    except Exception as e:
        print(f"Error cleaning up: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Demo wallet topup flow')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup demo data')
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_demo_data()
    else:
        demo_wallet_topup()