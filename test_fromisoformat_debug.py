#!/usr/bin/env python3
"""Test script to catch fromisoformat error source"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# Monkey patch fromisoformat to catch calls
original_fromisoformat = None

def debug_fromisoformat(cls, date_string):
    """Debug wrapper for fromisoformat to catch problematic calls"""
    print(f"🚨 FROMISOFORMAT CALLED: {repr(date_string)} ({type(date_string)})", flush=True)
    import traceback
    print("📍 Call stack:")
    for line in traceback.format_stack()[-5:]:
        print(f"   {line.strip()}")
    print("-" * 60, flush=True)
    
    # Call original
    return original_fromisoformat(date_string)

# Apply monkey patch
from datetime import datetime
original_fromisoformat = datetime.fromisoformat
datetime.fromisoformat = classmethod(debug_fromisoformat)

# Now test import for company 104
from apps.stock.services.symbol_service import SymbolService
from apps.stock.models import Company

def test_company_104():
    print("🔍 TESTING COMPANY 104 IMPORT")
    print("=" * 60)
    
    try:
        company = Company.objects.get(id=104)
        print(f"📊 Company 104: {company.company_name}")
        
        # Get symbol
        symbol = company.symbols.first()
        if not symbol:
            print("❌ No symbol found")
            return
            
        print(f"🏷️  Symbol: {symbol.name}")
        
        # Try import
        service = SymbolService()
        result = service.import_company_by_id(104)
        print(f"✅ Import result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_company_104()