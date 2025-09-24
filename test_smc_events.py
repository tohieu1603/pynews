#!/usr/bin/env python3
"""Simple test to trigger fromisoformat error"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from vnstock import Company as VNStockCompany
from apps.stock.utils.safe import to_datetime

# Test with SMC company
print("🔍 TESTING SMC EVENTS DATA")
print("=" * 50)

try:
    vnstock_company = VNStockCompany(symbol="SMC", source="VCI")
    events_data = vnstock_company.events()
    print(f"Events shape: {events_data.shape}")
    
    if not events_data.empty:
        # Test first few rows
        for idx, row in events_data.head(3).iterrows():
            print(f"\n🔸 Row {idx}:")
            for field in ['public_date', 'issue_date']:
                if field in row:
                    raw_value = row[field]
                    print(f"   {field}: {repr(raw_value)} ({type(raw_value)})")
                    
                    # Test to_datetime conversion
                    try:
                        result = to_datetime(raw_value)
                        print(f"   -> Converted: {result}")
                    except Exception as e:
                        print(f"   -> ERROR: {e}")
    else:
        print("No events data")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()