from ninja import Schema
from typing import List, Optional
from datetime import datetime


# ---- Shareholder ----
class ShareHolderOut(Schema):
    id: int
    share_holder: Optional[str] = None
    quantity: Optional[int] = None
    share_own_percent: Optional[float] = None
    update_date: Optional[datetime] = None


# ---- News ----
class NewsOut(Schema):
    id: int
    title: Optional[str] = None
    news_image_url: Optional[str] = None   # sửa cho khớp với model
    news_source_link: Optional[str] = None # sửa cho khớp với model
    price_change_pct: Optional[float] = None
    public_date: Optional[int] = None  # model lưu epoch (BigIntegerField)


# ---- Events ----
class EventsOut(Schema):
    id: int
    event_title: Optional[str] = None
    public_date: Optional[datetime] = None
    issue_date: Optional[datetime] = None
    source_url: Optional[str] = None


# ---- Officers ----
class OfficersOut(Schema):
    id: int
    officer_name: Optional[str] = None
    officer_position: Optional[str] = None
    position_short_name: Optional[str] = None
    officer_owner_percent: Optional[float] = None
    updated_at: Optional[datetime] = None


# ---- SubCompany ----
class SubCompanyOut(Schema):
    id: int
    company_name: Optional[str] = None
    sub_own_percent: Optional[float] = None


# ---- Company ----
class CompanyOut(Schema):
    id: int
    company_name: str
    company_profile: Optional[str] = None
    history: Optional[str] = None
    issue_share: Optional[int] = None
    financial_ratio_issue_share: Optional[int] = None
    charter_capital: Optional[int] = None
    outstanding_share: Optional[float] = None
    foreign_percent: Optional[float] = None
    established_year: Optional[int] = None
    no_employees: Optional[int] = None
    stock_rating: Optional[float] = None
    website: Optional[str] = None
    updated_at: Optional[datetime] = None
    shareholders: List[ShareHolderOut] = []
    news: List[NewsOut] = []
    events: List[EventsOut] = []
    officers: List[OfficersOut] = []
    subsidiaries: List[SubCompanyOut] = []


# ---- Industry (ref) ----
class IndustryRefOut(Schema):
    id: int
    name: str
    updated_at: Optional[datetime] = None


# ---- Symbol ----
class SymbolOut(Schema):
    id: int
    name: str
    exchange: Optional[str] = None
    updated_at: Optional[datetime] = None
    industries: List[IndustryRefOut] = []
    company: Optional[CompanyOut] = None
class SymbolList(Schema):
    id: int
    name: str
    exchange: str
    updated_at: datetime

# ---- Industry ----
class IndustryOut(Schema):
    id: int
    name: str
    updated_at: Optional[datetime] = None
    companies: List[CompanyOut] = []   # model có related_name='companies'
