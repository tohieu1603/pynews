#!/usr/bin/env python
"""
🔍 Debug News Import Issues

CÁCH SỬ DỤNG:
1. python tests/debug_news_null.py
2. Để check symbol cụ thể: python -c "from tests.debug_news_null import debug_symbol; debug_symbol('SVC')"

MỤC ĐÍCH:
- Debug tại sao news có "No Title" và các fields null
- Kiểm tra raw data từ VNStock
- Verify mapping process
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def debug_symbol(symbol_name='SVC'):
    """Debug news import cho symbol cụ thể"""
    
    print(f"🔍 DEBUG NEWS IMPORT FOR: {symbol_name}")
    print("=" * 60)
    
    from apps.stock.clients.vnstock_client import VNStockClient
    from apps.stock.services.mappers import DataMappers
    from apps.stock.models import Symbol, Company, News
    
    # 1. Check symbol in DB
    try:
        symbol = Symbol.objects.get(name=symbol_name)
        print(f"✅ Symbol found: {symbol.name}")
        
        if symbol.company:
            print(f"✅ Company linked: {symbol.company.company_name}")
            
            # Check current news in DB
            news_in_db = News.objects.filter(company=symbol.company)
            print(f"📊 Current news in DB: {news_in_db.count()}")
            
            if news_in_db.exists():
                sample_news = news_in_db.first()
                print(f"📰 Sample DB news:")
                print(f"   Title: '{sample_news.title}'")
                print(f"   Image URL: {sample_news.news_image_url}")
                print(f"   Source Link: {sample_news.news_source_link}")
                print(f"   Public Date: {sample_news.public_date}")
                print(f"   Price Change: {sample_news.price_change_pct}")
        else:
            print("❌ No company linked")
            return
            
    except Symbol.DoesNotExist:
        print(f"❌ Symbol {symbol_name} not found")
        return
    
    print()
    
    # 2. Fetch raw data from VNStock
    print(f"🔍 FETCHING RAW DATA FROM VNSTOCK...")
    
    client = VNStockClient()
    bundle, ok = client.fetch_company_bundle_safe(symbol_name)
    
    if not ok:
        print(f"❌ Failed to fetch bundle")
        return
        
    news_df = bundle.get("news_df")
    events_df = bundle.get("events_df")
    
    # 3. Analyze raw news data
    print(f"📰 RAW NEWS DATA ANALYSIS:")
    if news_df is not None and not news_df.empty:
        print(f"   ✅ News DataFrame shape: {news_df.shape}")
        print(f"   📋 Columns: {list(news_df.columns)}")
        
        # Check news_title field specifically
        if 'news_title' in news_df.columns:
            titles = news_df['news_title'].dropna()
            print(f"   📝 Non-null titles: {len(titles)}/{len(news_df)}")
            
            if not titles.empty:
                print(f"   📋 Sample titles:")
                for i, title in enumerate(titles.head(3)):
                    print(f"      {i+1}. '{title}'")
            else:
                print(f"   ❌ All titles are null!")
                
        # Check other key fields
        key_fields = ['news_image_url', 'news_source_link', 'public_date', 'price_change_pct']
        for field in key_fields:
            if field in news_df.columns:
                non_null = news_df[field].notna().sum()
                print(f"   📊 {field}: {non_null}/{len(news_df)} non-null")
            else:
                print(f"   ❌ {field}: Missing column!")
                
    else:
        print(f"   ❌ News DataFrame is empty or None!")
        print(f"   📋 Bundle keys: {list(bundle.keys())}")
    
    print()
    
    # 4. Analyze raw events data (might be confused with news)
    print(f"📅 RAW EVENTS DATA ANALYSIS:")
    if events_df is not None and not events_df.empty:
        print(f"   ✅ Events DataFrame shape: {events_df.shape}")
        print(f"   📋 Columns: {list(events_df.columns)}")
        
        # Show sample events
        print(f"   📋 Sample events:")
        for i, (_, row) in enumerate(events_df.head(3).iterrows()):
            event_title = row.get('event_title', 'No event_title column')
            print(f"      {i+1}. '{event_title}'")
            
    else:
        print(f"   ❌ Events DataFrame is empty or None!")
    
    print()
    
    # 5. Test mapping process
    print(f"🗂️  TESTING MAPPING PROCESS...")
    
    if news_df is not None and not news_df.empty:
        try:
            mapped_news = DataMappers.map_news(news_df)
            print(f"   ✅ News mapping successful: {len(mapped_news)} items")
            
            if mapped_news:
                sample_mapped = mapped_news[0]
                print(f"   📋 Sample mapped news:")
                for key, value in sample_mapped.items():
                    print(f"      {key}: '{value}'")
                    
        except Exception as e:
            print(f"   ❌ News mapping failed: {e}")
            import traceback
            traceback.print_exc()
    
    if events_df is not None and not events_df.empty:
        try:
            mapped_events = DataMappers.map_events(events_df)
            print(f"   ✅ Events mapping successful: {len(mapped_events)} items")
            
            if mapped_events:
                sample_mapped_event = mapped_events[0]
                print(f"   📋 Sample mapped event:")
                for key, value in sample_mapped_event.items():
                    print(f"      {key}: '{value}'")
                    
        except Exception as e:
            print(f"   ❌ Events mapping failed: {e}")
    
    print("=" * 60)

def check_all_news_in_db():
    """Check all news records in database"""
    
    print("📊 DATABASE NEWS ANALYSIS")
    print("=" * 50)
    
    from apps.stock.models import News, Company
    
    total_news = News.objects.count()
    print(f"📈 Total news records: {total_news}")
    
    # Check for "No Title" records
    no_title_news = News.objects.filter(title="No Title")
    print(f"❌ Records with 'No Title': {no_title_news.count()}")
    
    # Check for empty/null fields
    null_image = News.objects.filter(news_image_url__isnull=True).count()
    null_source = News.objects.filter(news_source_link__isnull=True).count()
    null_date = News.objects.filter(public_date__isnull=True).count()
    null_price = News.objects.filter(price_change_pct__isnull=True).count()
    
    print(f"📊 Null field analysis:")
    print(f"   Image URL null: {null_image}/{total_news}")
    print(f"   Source link null: {null_source}/{total_news}")
    print(f"   Public date null: {null_date}/{total_news}")
    print(f"   Price change null: {null_price}/{total_news}")
    
    # Show sample problematic records
    if no_title_news.exists():
        print(f"\n📋 Sample 'No Title' records:")
        for i, news in enumerate(no_title_news[:3]):
            print(f"   {i+1}. Company: {news.company.company_name if news.company else 'No company'}")
            print(f"      Title: '{news.title}'")
            print(f"      Image: {news.news_image_url}")
            print(f"      Source: {news.news_source_link}")
            print(f"      Date: {news.public_date}")
    
    print("=" * 50)

if __name__ == "__main__":
    print("🔍 NEWS IMPORT DEBUG SUITE")
    print("=" * 50)
    print()
    
    # Check current DB state
    check_all_news_in_db()
    print()
    
    # Debug specific symbol
    debug_symbol('SVC')
    
    print()
    print("💡 Next steps:")
    print("  1. Check if VNStock is returning empty news data")
    print("  2. Verify mapping logic is correct")  
    print("  3. Check if events are being saved as news by mistake")
    print("  4. Test with different symbols")