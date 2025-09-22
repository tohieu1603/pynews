from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User

from ..models import (
    PayWallet, PayWalletLedger, PaySymbolOrder, PaySymbolOrderItem, 
    PayUserSymbolLicense, PayPaymentIntent, WalletTxType, OrderStatus,
    PaymentMethod, LicenseStatus, IntentPurpose
)
from .wallet_topup_service import WalletTopupService


class SymbolPurchaseService:
    """Service xử lý việc mua quyền truy cập symbol (mã chứng khoán)"""
    
    def __init__(self):
        self.wallet_service = WalletTopupService()
    
    @transaction.atomic
    def create_symbol_order(
        self, 
        user: User, 
        items: List[Dict], 
        payment_method: str,
        description: str = None
    ) -> PaySymbolOrder:
        """
        Tạo đơn hàng mua quyền truy cập symbol
        
        Args:
            user: User thực hiện mua
            items: List[{symbol_id, price, license_days, metadata}]
            payment_method: 'wallet' hoặc 'sepay_transfer'  
            description: Mô tả đơn hàng
        
        Returns:
            PaySymbolOrder instance
        """
        # Validate payment method
        if payment_method not in [PaymentMethod.WALLET, PaymentMethod.SEPAY_TRANSFER]:
            raise ValueError(f"Invalid payment method: {payment_method}")
        
        # Validate items
        if not items:
            raise ValueError("Order must have at least one item")
        
        for item in items:
            if not all(k in item for k in ['symbol_id', 'price']):
                raise ValueError("Each item must have symbol_id and price")
            if item['price'] <= 0:
                raise ValueError("Price must be positive")
        
        # Calculate total amount
        total_amount = sum(Decimal(str(item['price'])) for item in items)
        
        # Check wallet balance if payment method is wallet
        if payment_method == PaymentMethod.WALLET:
            try:
                wallet = PayWallet.objects.get(user=user)
                if wallet.balance < total_amount:
                    raise ValueError(
                        f"Insufficient wallet balance. Required: {total_amount} VND, "
                        f"Available: {wallet.balance} VND"
                    )
            except PayWallet.DoesNotExist:
                raise ValueError("User wallet not found. Please create a wallet first.")
        
        # Create order
        order = PaySymbolOrder.objects.create(
            user=user,
            total_amount=total_amount,
            status=OrderStatus.PENDING_PAYMENT,
            payment_method=payment_method,
            description=description or f"Mua quyền truy cập {len(items)} symbol"
        )
        
        # Create order items
        for item_data in items:
            PaySymbolOrderItem.objects.create(
                order=order,
                symbol_id=item_data['symbol_id'],
                price=Decimal(str(item_data['price'])),
                license_days=item_data.get('license_days'),
                metadata=item_data.get('metadata', {})
            )
        
        return order
    
    @transaction.atomic
    def process_wallet_payment(self, order_id: str, user: User) -> Dict:
        """
        Xử lý thanh toán bằng ví cho đơn hàng symbol
        
        Args:
            order_id: UUID của đơn hàng
            user: User thực hiện thanh toán
        
        Returns:
            Dict với thông tin kết quả thanh toán
        """
        try:
            # Get order
            order = PaySymbolOrder.objects.get(order_id=order_id, user=user)
            
            if order.status != OrderStatus.PENDING_PAYMENT:
                raise ValueError(f"Order status is {order.status}, cannot process payment")
            
            if order.payment_method != PaymentMethod.WALLET:
                raise ValueError(f"Order payment method is {order.payment_method}, not wallet")
            
            # Get user wallet
            wallet = PayWallet.objects.get(user=user)
            
            # Check balance
            if wallet.balance < order.total_amount:
                raise ValueError(
                    f"Insufficient balance. Required: {order.total_amount}, "
                    f"Available: {wallet.balance}"
                )
            
            # Create ledger entry
            ledger_entry = PayWalletLedger.objects.create(
                wallet=wallet,
                tx_type=WalletTxType.PURCHASE,
                amount=order.total_amount,
                is_credit=False,  # Debit (subtract from wallet)
                balance_before=wallet.balance,
                balance_after=wallet.balance - order.total_amount,
                order_id=order.order_id,
                note=f"Mua quyền truy cập symbol - Order {order.order_id}"
            )
            
            # Update wallet balance
            wallet.balance = ledger_entry.balance_after
            wallet.save()
            
            # Update order status
            order.status = OrderStatus.PAID
            order.save()
            
            # Create licenses
            licenses_created = self._create_symbol_licenses(order)
            
            return {
                'success': True,
                'message': 'Payment processed successfully',
                'order_id': str(order.order_id),
                'amount_charged': float(order.total_amount),
                'wallet_balance_after': float(wallet.balance),
                'licenses_created': licenses_created
            }
            
        except PaySymbolOrder.DoesNotExist:
            raise ValueError("Order not found")
        except PayWallet.DoesNotExist:
            raise ValueError("User wallet not found")
    
    def create_sepay_payment_intent(self, order_id: str, user: User) -> Dict:
        """
        Tạo payment intent cho thanh toán SePay
        
        Args:
            order_id: UUID của đơn hàng
            user: User thực hiện thanh toán
        
        Returns:
            Dict với thông tin payment intent và QR code
        """
        try:
            # Get order
            order = PaySymbolOrder.objects.get(order_id=order_id, user=user)
            
            if order.status != OrderStatus.PENDING_PAYMENT:
                raise ValueError(f"Order status is {order.status}, cannot create payment intent")
            
            if order.payment_method != PaymentMethod.SEPAY_TRANSFER:
                raise ValueError(f"Order payment method is {order.payment_method}, not sepay_transfer")
            
            # Create payment intent
            intent_result = self.wallet_service.create_payment_intent(
                user=user,
                amount=order.total_amount,
                purpose=IntentPurpose.ORDER_PAYMENT,
                metadata={
                    'order_id': str(order.order_id),
                    'order_type': 'symbol_purchase',
                    'items_count': order.items.count()
                }
            )
            
            # Link order to payment intent
            intent = PayPaymentIntent.objects.get(intent_id=intent_result['intent_id'])
            order.payment_intent = intent
            order.save()
            
            return intent_result
            
        except PaySymbolOrder.DoesNotExist:
            raise ValueError("Order not found")
    
    def process_sepay_payment_completion(self, payment_id: str) -> Dict:
        """
        Xử lý hoàn tất thanh toán SePay cho đơn hàng symbol
        
        Args:
            payment_id: UUID của payment đã hoàn thành
        
        Returns:
            Dict với thông tin kết quả
        """
        from ..models import PayPayment
        
        try:
            # Get payment
            payment = PayPayment.objects.get(payment_id=payment_id)
            
            if not payment.order_id:
                raise ValueError("Payment is not linked to any order")
            
            # Get order
            order = PaySymbolOrder.objects.get(order_id=payment.order_id)
            
            if order.status == OrderStatus.PAID:
                return {
                    'success': True,
                    'message': 'Order already processed',
                    'order_id': str(order.order_id)
                }
            
            # Update order status
            order.status = OrderStatus.PAID
            order.save()
            
            # Create licenses
            licenses_created = self._create_symbol_licenses(order)
            
            return {
                'success': True,
                'message': 'SePay payment completed and licenses created',
                'order_id': str(order.order_id),
                'payment_id': str(payment.payment_id),
                'licenses_created': licenses_created
            }
            
        except (PayPayment.DoesNotExist, PaySymbolOrder.DoesNotExist):
            raise ValueError("Payment or order not found")
    
    def _create_symbol_licenses(self, order: PaySymbolOrder) -> int:
        """
        Tạo license cho user dựa trên order items
        
        Args:
            order: PaySymbolOrder instance
        
        Returns:
            Số lượng license được tạo/cập nhật
        """
        licenses_created = 0
        now = timezone.now()
        
        for item in order.items.all():
            # Calculate license period
            start_at = now
            end_at = None
            if item.license_days:
                end_at = start_at + timedelta(days=item.license_days)
            
            # Check existing license
            existing_license = PayUserSymbolLicense.objects.filter(
                user=order.user,
                symbol_id=item.symbol_id,
                status=LicenseStatus.ACTIVE
            ).first()
            
            if existing_license:
                # Extend existing license
                if existing_license.end_at and end_at:
                    # Both have expiry - extend to later date
                    existing_license.end_at = max(existing_license.end_at, end_at)
                elif not end_at:
                    # New license is lifetime - upgrade existing
                    existing_license.end_at = None
                # If existing is lifetime and new has expiry, keep lifetime
                
                existing_license.save()
                licenses_created += 1
            else:
                # Create new license
                PayUserSymbolLicense.objects.create(
                    user=order.user,
                    symbol_id=item.symbol_id,
                    order=order,
                    status=LicenseStatus.ACTIVE,
                    start_at=start_at,
                    end_at=end_at
                )
                licenses_created += 1
        
        return licenses_created
    
    def check_symbol_access(self, user: User, symbol_id: int) -> Dict:
        """
        Kiểm tra quyền truy cập symbol của user
        
        Args:
            user: User cần kiểm tra
            symbol_id: ID của symbol cần kiểm tra
        
        Returns:
            Dict với thông tin quyền truy cập
        """
        try:
            license = PayUserSymbolLicense.objects.filter(
                user=user,
                symbol_id=symbol_id,
                status=LicenseStatus.ACTIVE
            ).first()
            
            if not license:
                return {
                    'has_access': False,
                    'reason': 'No active license found'
                }
            
            now = timezone.now()
            
            # Check if license is expired
            if license.end_at and license.end_at <= now:
                # Mark as expired
                license.status = LicenseStatus.EXPIRED
                license.save()
                
                return {
                    'has_access': False,
                    'reason': 'License expired',
                    'expired_at': license.end_at.isoformat()
                }
            
            # Calculate time until expiry
            expires_soon = False
            if license.end_at:
                time_until_expiry = license.end_at - now
                expires_soon = time_until_expiry.days <= 7  # Warning if < 7 days
            
            return {
                'has_access': True,
                'license_id': str(license.license_id),
                'start_at': license.start_at.isoformat(),
                'end_at': license.end_at.isoformat() if license.end_at else None,
                'is_lifetime': license.end_at is None,
                'expires_soon': expires_soon
            }
            
        except Exception as e:
            return {
                'has_access': False,
                'reason': f'Error checking access: {str(e)}'
            }
    
    def get_user_symbol_licenses(self, user: User, page: int = 1, limit: int = 20) -> Dict:
        """
        Lấy danh sách license của user
        
        Args:
            user: User cần lấy license
            page: Trang (1-indexed)
            limit: Số license mỗi trang
        
        Returns:
            Dict với danh sách license và phân trang
        """
        offset = (page - 1) * limit
        
        licenses = PayUserSymbolLicense.objects.filter(user=user).order_by('-created_at')
        total = licenses.count()
        
        license_list = []
        for license in licenses[offset:offset + limit]:
            license_list.append({
                'license_id': str(license.license_id),
                'symbol_id': license.symbol_id,
                'status': license.status,
                'start_at': license.start_at.isoformat(),
                'end_at': license.end_at.isoformat() if license.end_at else None,
                'is_lifetime': license.end_at is None,
                'order_id': str(license.order_id) if license.order_id else None,
                'created_at': license.created_at.isoformat()
            })
        
        return {
            'results': license_list,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }
    
    def get_order_history(self, user: User, page: int = 1, limit: int = 20) -> Dict:
        """
        Lấy lịch sử mua symbol của user
        
        Args:
            user: User cần lấy lịch sử
            page: Trang (1-indexed) 
            limit: Số order mỗi trang
        
        Returns:
            Dict với danh sách order và phân trang
        """
        offset = (page - 1) * limit
        
        orders = PaySymbolOrder.objects.filter(user=user).order_by('-created_at')
        total = orders.count()
        
        order_list = []
        for order in orders[offset:offset + limit]:
            # Get items
            items = []
            for item in order.items.all():
                items.append({
                    'symbol_id': item.symbol_id,
                    'price': float(item.price),
                    'license_days': item.license_days,
                    'metadata': item.metadata
                })
            
            order_list.append({
                'order_id': str(order.order_id),
                'total_amount': float(order.total_amount),
                'status': order.status,
                'payment_method': order.payment_method,
                'description': order.description,
                'items': items,
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat()
            })
        
        return {
            'results': order_list,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }