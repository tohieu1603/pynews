#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.stock.services.vnstock_import_service import VnstockImportService
from apps.stock.models import Symbol

print(f'Current symbols in DB: {Symbol.objects.count()}')

service = VnstockImportService(per_symbol_sleep=0.5)

if Symbol.objects.count() == 0:
    print('No symbols found, running symbol import first...')
    results = service.import_all_symbols_from_vnstock('HSX')
    print(f'Imported {len(results)} symbols')

print('Testing complete import...')
results = service.import_all_data_sequential('HSX')
print('\nFinal Summary:')
print(results.get('summary', {}))
print('\nErrors:')
for error in results.get('errors', []):
    print(f'  - {error}')