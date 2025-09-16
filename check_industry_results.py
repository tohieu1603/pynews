#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.stock.models import Symbol, Industry

def check_industry_results():
    print("=== Industry Import Results ===")
    
    total_industries = Industry.objects.count()
    total_symbols = Symbol.objects.count()
    symbols_with_industries = Symbol.objects.filter(industries__isnull=False).distinct().count()
    
    print(f"Total Industries in DB: {total_industries}")
    print(f"Total Symbols: {total_symbols}")
    print(f"Symbols with Industries: {symbols_with_industries}")
    print(f"Progress: {symbols_with_industries}/{total_symbols} ({symbols_with_industries/total_symbols*100:.1f}%)")
    
    print("\nSample symbols with industries:")
    for symbol in Symbol.objects.filter(industries__isnull=False).distinct()[:10]:
        industries = symbol.industries.all()
        print(f"  {symbol.name} -> {len(industries)} industries:")
        for industry in industries[:2]:  # Show first 2 industries
            print(f"    - {industry.name} (ID: {industry.id})")
    
    print("\nSample industries with symbols:")
    for industry in Industry.objects.all()[:5]:
        symbol_count = industry.symbols.count()
        print(f"  {industry.name} (ID: {industry.id}) -> {symbol_count} symbols")
        if symbol_count > 0:
            symbols = industry.symbols.all()[:3]
            print(f"    Sample symbols: {[s.name for s in symbols]}")
    
    # Test specific case: VTO
    print("\n=== VTO Industry Test (as mentioned by user) ===")
    try:
        vto_symbol = Symbol.objects.get(name='VTO')
        vto_industries = vto_symbol.industries.all()
        print(f"VTO has {len(vto_industries)} industries:")
        for industry in vto_industries:
            print(f"  - {industry.name} (Code: {industry.id})")
    except Symbol.DoesNotExist:
        print("VTO symbol not found")

if __name__ == "__main__":
    check_industry_results()