#!/usr/bin/env python3
"""Debug script for company 83 fromisoformat error"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.stock.services.company_processor import CompanyProcessor
from apps.stock.models import Company
from apps.stock.utils.safe import to_datetime, to_epoch_seconds

def debug_company_83():
    print("🔍 DEBUG COMPANY 83 FROMISOFORMAT ERROR", flush=True)
    print("=" * 60, flush=True)
    
    try:
        # Find company with ID 83
        company = Company.objects.get(id=83)
        print(f"📊 Company 83: {company.company_name}")
        
        # Get symbol for this company
        symbol = company.symbols.first()
        if not symbol:
            print(f"❌ No symbol found for company {company.company_name}")
            return
            
        print(f"🏷️  Symbol: {symbol.name}")
        
        processor = CompanyProcessor()
        
        # Override the process method to catch the specific error
        print(f"\n🔍 Testing data fetch for {symbol.name}...")
        
        try:
            from vnstock import Company as VNStockCompany
            vnstock_company = VNStockCompany(symbol=symbol.name, source="VCI")
            
            # Test getting news data
            print(f"📰 Fetching news data...")
            news_data = vnstock_company.news()
            print(f"   Shape: {news_data.shape}")
            
            if not news_data.empty:
                # Check problematic datetime fields
                for idx, row in news_data.iterrows():
                    print(f"\n🔸 Testing row {idx}:")
                    
                    for field in ['public_date', 'created_at', 'updated_at']:
                        if field in row:
                            raw_value = row[field]
                            print(f"   {field}: {repr(raw_value)} ({type(raw_value)})")
                            
                            # Test conversion
                            try:
                                epoch_result = to_epoch_seconds(raw_value)
                                print(f"     -> to_epoch_seconds: {epoch_result}")
                            except Exception as e:
                                print(f"     -> to_epoch_seconds ERROR: {e}")
                            
                            try:
                                dt_result = to_datetime(raw_value)
                                print(f"     -> to_datetime: {dt_result}")
                            except Exception as e:
                                print(f"     -> to_datetime ERROR: {e}")
                    
                    # Only test first few rows to avoid spam
                    if idx >= 2:
                        break
            else:
                print(f"❌ No news data available for {symbol.name}")
                
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            import traceback
            traceback.print_exc()
            
    except Company.DoesNotExist:
        print("❌ Company with ID 83 does not exist")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_company_83()