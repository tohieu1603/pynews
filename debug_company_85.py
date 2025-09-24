#!/usr/bin/env python3
"""Debug script for company 85 fromisoformat error"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.stock.services.symbol_service import SymbolService

def debug_company_85():
    print("🔍 DEBUG COMPANY 85 FROMISOFORMAT ERROR", flush=True)
    print("=" * 60, flush=True)
    
    try:
        service = SymbolService()
        print("🚀 Triggering import for company 85...", flush=True)
        
        # This should trigger the error with debug output
        result = service.import_company_by_id(85)
        print(f"✅ Import result: {result}", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_company_85()