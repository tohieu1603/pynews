from ninja import NinjaAPI
from apps.stock.routers.vnstock_import import router as stock_router
from apps.account.api import router as account_router
from apps.calculate.routers.calculate import router as calculate_router
from apps.setting.api import router as setting_router
from apps.seapay.api import router as seapay_router
api = NinjaAPI(title="Togogo Analysis API", version="1.0.0")

# Routers
api.add_router("/auth/", account_router, tags=["Authentication"]) 
api.add_router("/stocks/", stock_router, tags=["Stocks"])
api.add_router("/calculate/", calculate_router, tags=["Financial Calculations"])
api.add_router("/settings/", setting_router, tags=["Settings"])
api.add_router("/sepay/", seapay_router, tags=["Sepay Payment"])
