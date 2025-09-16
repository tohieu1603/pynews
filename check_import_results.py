#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.stock.models import Symbol, Company

def check_import_results():
    print("=== Company Import Results ===")
    
    total_companies = Company.objects.count()
    symbols_with_company = Symbol.objects.filter(company__isnull=False).count()
    total_symbols = Symbol.objects.count()
    
    print(f"Total Companies in DB: {total_companies}")
    print(f"Total Symbols: {total_symbols}")
    print(f"Symbols with Company: {symbols_with_company}")
    print(f"Progress: {symbols_with_company}/{total_symbols} ({symbols_with_company/total_symbols*100:.1f}%)")
    
    print("\nSample symbols with companies:")
    for s in Symbol.objects.filter(company__isnull=False)[:10]:
        print(f"  {s.name} -> {s.company.company_name}")
    
    print("\nSample companies created:")
    for c in Company.objects.all()[:5]:
        print(f"  {c.company_name}")
        print(f"    - Profile length: {len(c.company_profile or '')}")
        print(f"    - History length: {len(c.history or '')}")
        print(f"    - Issue share: {c.issue_share}")
        print(f"    - Website: {c.website}")

if __name__ == "__main__":
    check_import_results()