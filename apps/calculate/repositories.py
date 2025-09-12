
from typing import Dict
from apps.calculate.models import BalanceSheet

def upsert_blance_sheet(defaults: Dict) -> None:
    """
    Tạo hoặc update bảng cân đối kế toán cho một Symbol
    """
    BalanceSheet.objects.update_or_create(
        defaults=defaults
    )
    