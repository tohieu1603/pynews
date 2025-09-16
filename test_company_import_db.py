#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.stock.services.vnstock_import_service import VnstockImportService
from apps.stock.models import Symbol, Company

def test_company_import_with_db():
    print("=== Testing Company Import with Database Update ===")
    
    # Lấy 5 symbols đầu tiên để test
    symbols = Symbol.objects.all()[:5]
    print(f"Testing with {len(symbols)} symbols: {[s.name for s in symbols]}")
    
    service = VnstockImportService(per_symbol_sleep=1.0)
    
    # Test import companies
    try:
        print("\n--- Before import ---")
        companies_before = Company.objects.count()
        symbols_with_company_before = Symbol.objects.filter(company__isnull=False).count()
        print(f"Companies in DB: {companies_before}")
        print(f"Symbols with company: {symbols_with_company_before}")
        
        print("\n--- Running import ---")
        results = service.import_companies_from_vnstock()
        
        print(f"\n--- After import ---")
        companies_after = Company.objects.count()
        symbols_with_company_after = Symbol.objects.filter(company__isnull=False).count()
        print(f"Companies in DB: {companies_after}")
        print(f"Symbols with company: {symbols_with_company_after}")
        
        print(f"\n--- Results ---")
        print(f"Import results: {len(results)} records")
        if results:
            print("Sample results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result}")
        
        print("\n--- Verification ---")
        # Verify một số symbols có company hay chưa
        for symbol in symbols[:3]:
            symbol.refresh_from_db()
            if symbol.company:
                print(f"✓ {symbol.name} -> {symbol.company.company_name}")
            else:
                print(f"✗ {symbol.name} -> No company")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_company_import_with_db()