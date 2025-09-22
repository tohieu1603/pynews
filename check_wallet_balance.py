#!/usr/bin/env python3
"""
Script kiểm tra số dư ví từ JWT token
"""
import os
import django
import jwt
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.seapay.models import PayWallet
from django.contrib.auth import get_user_model

User = get_user_model()

def check_wallet_balance(token):
    """Kiểm tra số dư ví từ JWT token"""
    try:
        # Decode JWT token (không verify signature vì chỉ cần lấy user_id)
        payload = jwt.decode(token, options={'verify_signature': False})
        user_id = payload.get('user_id')
        email = payload.get('email')
        
        print('🔍 Token Info:')
        print(f'- User ID: {user_id}')
        print(f'- Email: {email}')
        print(f'- IAT: {payload.get("iat")}')
        print(f'- EXP: {payload.get("exp")}')
        print('-' * 50)
        
        # Lấy thông tin user
        try:
            user = User.objects.get(id=user_id)
            print(f'👤 User found: {user.username} ({user.email})')
            
            # Kiểm tra ví của user
            try:
                wallet = PayWallet.objects.get(user=user)
                print('')
                print('💰 Wallet Info:')
                print(f'- Wallet ID: {wallet.id}')
                print(f'- Balance: {wallet.balance:,.0f} VND')
                print(f'- Currency: {wallet.currency}')
                print(f'- Status: {wallet.status}')
                print(f'- Created: {wallet.created_at}')
                print(f'- Updated: {wallet.updated_at}')
                
                # Summary
                print('')
                print('📊 SUMMARY:')
                print(f'🔸 User: {user.username}')
                print(f'🔸 Current Balance: {wallet.balance:,.0f} VND')
                print(f'🔸 Wallet Status: {wallet.status}')
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'username': user.username,
                    'email': user.email,
                    'wallet_id': wallet.id,
                    'wallet_balance': float(wallet.balance),
                    'currency': wallet.currency,
                    'wallet_status': wallet.status
                }
                
            except PayWallet.DoesNotExist:
                print('❌ Wallet not found for this user')
                return {'success': False, 'error': 'Wallet not found'}
                
        except User.DoesNotExist:
            print(f'❌ User with ID {user_id} not found')
            return {'success': False, 'error': f'User with ID {user_id} not found'}
            
    except Exception as e:
        print(f'❌ Error decoding token: {e}')
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    # Token từ request
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJlbWFpbCI6ImhpZXV0dHBoNDc2MzlAZnB0LmVkdS52biIsImlhdCI6MTc1ODUyNTY2NCwiZXhwIjoxNzU4NTI5MjY0LCJ0eXBlIjoiYWNjZXNzIn0.xh2C-G9EGB9eQh77UneETvYMTwlQJTLIc0cFzEYRDFk'
    
    result = check_wallet_balance(token)
    print(f'\n🔄 Script completed. Result: {result["success"]}')