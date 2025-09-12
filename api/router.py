from ninja import NinjaAPI
from apps.stock.routers.stock import router as stock_router
from apps.account.api import router as account_router
api = NinjaAPI(title="Togogo Analysis API", version="1.0.0")

# Routers
api.add_router("/auth/", account_router, tags=["Authentication"]) 
api.add_router("/stocks/", stock_router, tags=["Stocks"])
# api.add_router("/calculate/", calculate_router, tags=["Financial Calculations"])
