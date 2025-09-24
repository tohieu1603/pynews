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
from .payment_service import PaymentService
from apps.stock.models import Symbol


class SymbolPurchaseService:
    """Service xử lý việc mua quyền truy cập symbol (mã chứng khoán)"""
    
    def __init__(self):
        self.payment_service = PaymentService()
    
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
        if payment_method not in [PaymentMethod.WALLET, PaymentMethod.SEPAY_TRANSFER]:
            raise ValueError(f"Invalid payment method: {payment_method}")
        
        if not items:
            raise ValueError("Order must have at least one item")
        
        for item in items:
            if not all(k in item for k in ['symbol_id', 'price']):
                raise ValueError("Each item must have symbol_id and price")
            if item['price'] <= 0:
                raise ValueError("Price must be positive")
        
        total_amount = sum(Decimal(str(item['price'])) for item in items)
        
        # Tạo order trước (với transaction riêng để đảm bảo được lưu)
        with transaction.atomic():
            order = PaySymbolOrder.objects.create(
                user=user,
                total_amount=total_amount,
                status=OrderStatus.PENDING_PAYMENT,
                payment_method=payment_method,
                description=description or f"Mua quyền truy cập {len(items)} symbol"
            )
            
            # Tạo order items
            for item_data in items:
                PaySymbolOrderItem.objects.create(
                    order=order,
                    symbol_id=item_data['symbol_id'],
                    price=Decimal(str(item_data['price'])),
                    license_days=item_data.get('license_days'),
                    metadata=item_data.get('metadata', {})
                )
        
        # Bây giờ order đã được lưu, check payment method
        if payment_method == PaymentMethod.WALLET:
            try:
                wallet = PayWallet.objects.get(user=user)
                if wallet.balance >= total_amount:
                    # Đủ số dư - process payment trong transaction riêng
                    return self._process_immediate_wallet_payment(order, wallet)
                else:
                    # Số dư không đủ - raise exception nhưng giữ order
                    insufficient_amount = total_amount - wallet.balance
                    raise ValueError({
                        "code": "INSUFFICIENT_BALANCE",
                        "message": f"Số dư không đủ. Cần thêm {insufficient_amount:,.0f} VND",
                        "required_amount": float(total_amount),
                        "current_balance": float(wallet.balance),
                        "insufficient_amount": float(insufficient_amount),
                        "order_id": str(order.order_id),
                        "topup_endpoint": f"/api/sepay/symbol/order/{order.order_id}/topup-sepay"
                    })
            except PayWallet.DoesNotExist:
                # Xóa order nếu không có wallet
                order.delete()
                raise ValueError("User wallet not found. Please create a wallet first.")
        else:
            self._create_sepay_payment_intent_for_order(order)
        
        return order
    
    def _create_sepay_payment_intent_for_order(self, order: PaySymbolOrder) -> None:
        """
        Tự động tạo SePay payment intent cho đơn hàng
        
        Args:
            order: PaySymbolOrder instance
        """
        try:
            # Create payment intent using PaymentService
            intent = self.payment_service.create_payment_intent(
                user=order.user,
                purpose=IntentPurpose.ORDER_PAYMENT,
                amount=order.total_amount,
                currency="VND",
                metadata={
                    'order_id': str(order.order_id),
                    'order_type': 'symbol_purchase',
                    'items_count': order.items.count(),
                    'auto_created': True
                }
            )
            
            # Link order to payment intent
            order.payment_intent = intent
            order.save()
            
        except Exception as e:
            # Log error but don't fail the order creation
            print(f"Failed to auto-create SePay payment intent for order {order.order_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_immediate_wallet_payment(self, order: PaySymbolOrder, wallet: PayWallet) -> PaySymbolOrder:
        """
        Xử lý thanh toán ví ngay lập tức khi tạo đơn hàng
        
        Args:
            order: PaySymbolOrder instance
            wallet: PayWallet instance
        
        Returns:
            PaySymbolOrder với trạng thái đã thanh toán
        """
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
        
        # Create licenses immediately
        self._create_symbol_licenses(order)
        
        return order
    
    def create_sepay_topup_for_insufficient_order(self, order_id: str, user: User) -> Dict:
        """
        Tạo SePay QR để nạp tiền khi số dư không đủ thanh toán đơn hàng
        
        Args:
            order_id: UUID của đơn hàng
            user: User thực hiện nạp tiền
        
        Returns:
            Dict với thông tin payment intent và QR code
        """
        try:
            # Get order
            order = PaySymbolOrder.objects.get(order_id=order_id, user=user)
            
            if order.status != OrderStatus.PENDING_PAYMENT:
                raise ValueError(f"Order status is {order.status}, cannot create top-up")
            
            if order.payment_method != PaymentMethod.WALLET:
                raise ValueError(f"Order payment method is {order.payment_method}, must be wallet for top-up")
            
            # Get current wallet balance
            wallet = PayWallet.objects.get(user=user)
            required_amount = order.total_amount - wallet.balance
            
            if required_amount <= 0:
                raise ValueError("Wallet balance is sufficient, no top-up needed")
            
            # Create payment intent for top-up using PaymentService
            intent = self.payment_service.create_payment_intent(
                user=user,
                purpose=IntentPurpose.WALLET_TOPUP,
                amount=required_amount,
                currency="VND",
                metadata={
                    'order_id': str(order.order_id),
                    'order_type': 'symbol_purchase_topup',
                    'required_amount': float(required_amount),
                    'current_balance': float(wallet.balance),
                    'order_total': float(order.total_amount)
                }
            )
            
            # Link order to payment intent
            order.payment_intent = intent
            order.save()
            
            return {
                'intent_id': str(intent.intent_id),
                'order_code': intent.order_code,
                'amount': required_amount,
                'currency': 'VND',
                'expires_at': intent.expires_at.isoformat() if intent.expires_at else None,
                'qr_code_url': intent.qr_code_url,
                'message': f"Tạo QR nạp thêm {required_amount:,.0f} VND để hoàn thành đơn hàng"
            }
            
        except PaySymbolOrder.DoesNotExist:
            raise ValueError("Order not found")
        except PayWallet.DoesNotExist:
            raise ValueError("User wallet not found")
    
    @transaction.atomic
    def process_wallet_payment(self, order_id: str, user: User) -> Dict:
        """
        Xử lý thanh toán bằng ví cho đơn hàng symbol
        """
        try:
            # Get order
            order = PaySymbolOrder.objects.get(order_id=order_id, user=user)
            
            if order.status != OrderStatus.PENDING_PAYMENT:
                raise ValueError(f"Order status is {order.status}, cannot process payment")
            
            if order.payment_method != PaymentMethod.WALLET:
                raise ValueError(f"Order payment method is {order.payment_method}, not wallet")
            
            wallet = PayWallet.objects.get(user=user)
            
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
            
            # Create payment intent using PaymentService
            intent = self.payment_service.create_payment_intent(
                user=user,
                purpose=IntentPurpose.ORDER_PAYMENT,
                amount=order.total_amount,
                currency="VND",
                metadata={
                    'order_id': str(order.order_id),
                    'order_type': 'symbol_purchase',
                    'items_count': order.items.count()
                }
            )
            
            # Link order to payment intent
            order.payment_intent = intent
            order.save()
            
            return {
                'intent_id': str(intent.intent_id),
                'qr_code_url': intent.qr_code_url,
                'deep_link': intent.deep_link
            }
            
        except PaySymbolOrder.DoesNotExist:
            raise ValueError("Order not found")
    
    def process_sepay_payment_completion(self, payment_id: str) -> Dict:
        """
        Xử lý hoàn tất thanh toán SePay cho đơn hàng symbol
        - Nếu là nạp ví để mua symbol: nạp tiền + tự động thanh toán đơn hàng
        - Nếu là thanh toán trực tiếp: tạo license
        
        Args:
            payment_id: UUID của payment đã hoàn thành
        
        Returns:
            Dict với thông tin kết quả
        """
        from ..models import PayPayment
        
        try:
            # Get payment
            payment = PayPayment.objects.get(payment_id=payment_id)
            
            # Check if this is wallet topup for order
            intent = payment.intent
            if intent and intent.purpose == IntentPurpose.WALLET_TOPUP:
                metadata = intent.metadata or {}
                order_id = metadata.get('order_id')
                
                if order_id:
                    # This is topup for insufficient order - process auto payment
                    return self._process_topup_and_auto_payment(payment, order_id)
            
            # Regular order payment processing
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
    
    @transaction.atomic
    def _process_topup_and_auto_payment(self, payment, order_id: str) -> Dict:
        """
        Xử lý nạp tiền và tự động thanh toán đơn hàng
        
        Args:
            payment: PayPayment instance của SePay
            order_id: UUID của đơn hàng cần thanh toán
        
        Returns:
            Dict với thông tin kết quả
        """
        try:
            # Get order
            order = PaySymbolOrder.objects.get(order_id=order_id)
            user = order.user
            
            # Get wallet (topup should have already been processed by webhook)
            wallet = PayWallet.objects.get(user=user)
            
            # Check if wallet now has sufficient balance
            if wallet.balance < order.total_amount:
                return {
                    'success': False,
                    'message': f'Wallet balance still insufficient after topup. Required: {order.total_amount}, Available: {wallet.balance}',
                    'order_id': str(order.order_id),
                    'topup_amount': float(payment.amount),
                    'current_balance': float(wallet.balance)
                }
            
            # Process automatic payment
            ledger_entry = PayWalletLedger.objects.create(
                wallet=wallet,
                tx_type=WalletTxType.PURCHASE,
                amount=order.total_amount,
                is_credit=False,  # Debit
                balance_before=wallet.balance,
                balance_after=wallet.balance - order.total_amount,
                order_id=order.order_id,
                note=f"Auto-payment after topup - Order {order.order_id}"
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
                'message': 'Topup completed and order automatically paid',
                'order_id': str(order.order_id),
                'topup_amount': float(payment.amount),
                'order_amount': float(order.total_amount),
                'wallet_balance_after': float(wallet.balance),
                'licenses_created': licenses_created,
                'auto_payment': True
            }
            
        except PaySymbolOrder.DoesNotExist:
            raise ValueError("Order not found")
        except PayWallet.DoesNotExist:
            raise ValueError("User wallet not found")
    
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
            # Check if license is active (not expired)
            now = timezone.now()
            is_active = (license.status == LicenseStatus.ACTIVE and 
                        (license.end_at is None or license.end_at > now))
            
            license_list.append({
                'license_id': str(license.license_id),
                'symbol_id': license.symbol_id,
                'status': license.status,
                'start_at': license.start_at.isoformat(),
                'end_at': license.end_at.isoformat() if license.end_at else None,
                'is_lifetime': license.end_at is None,
                'is_active': is_active,
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
    
    def get_order_history(
        self,
        user: User,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> Dict:
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

        if status is None:
            status_filter = [OrderStatus.PAID]
        else:
            status_filter = [status]

        orders_qs = (
            PaySymbolOrder.objects.filter(user=user, status__in=status_filter)
            .order_by('-created_at')
            .prefetch_related('items')
        )
        total = orders_qs.count()

        orders = list(orders_qs[offset:offset + limit])

        symbol_ids = {
            item.symbol_id
            for order in orders
            for item in order.items.all()
            if item.symbol_id
        }
        symbol_map = {
            symbol.id: symbol.name
            for symbol in Symbol.objects.filter(id__in=symbol_ids)
        } if symbol_ids else {}

        order_list = []
        for order in orders:
            # Get items
            items = []
            for item in order.items.all():
                items.append({
                    'symbol_id': item.symbol_id,
                    'symbol_name': symbol_map.get(item.symbol_id),
                    'price': item.price,
                    'license_days': item.license_days,
                    'metadata': item.metadata or {}
                })

            order_list.append({
                'order_id': str(order.order_id),
                'total_amount': order.total_amount,
                'status': order.status,
                'payment_method': order.payment_method,
                'description': order.description or "",
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

