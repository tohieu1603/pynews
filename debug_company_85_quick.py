#!/usr/bin/env python3
"""Quick debug script for company 85 fromisoformat error"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.stock.services.symbol_service import SymbolService

def main():
    print("🔍 DEBUG COMPANY 85 FROMISOFORMAT ERROR")
    print("=" * 60)
    
    try:
        service = SymbolService()
        print("📊 Triggering import for company 85...")
        result = service.import_company_by_id(85)
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()