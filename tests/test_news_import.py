#!/usr/bin/env python
"""
📰 Test News Import for Symbol Service

CÁCH SỬ DỤNG:
1. Chạy: python tests/test_news_import.py
2. Hoặc test symbol cụ thể: python -c "from tests.test_news_import import test_symbol_news; test_symbol_news('VIC')"

MỤC ĐÍCH:
- Test import news data cho symbols
- Debug news processing issues
- Verify news data trong database

REQUIREMENTS:
- Django environment setup
- VNStock client working
- Database connection
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def test_symbol_news(symbol_name='VIC'):
    """
    📰 Test news import cho symbol cụ thể
    
    CÁCH CHẠY:
        python -c "from tests.test_news_import import test_symbol_news; test_symbol_news('VIC')"
    
    PARAMETERS:
        symbol_name (str): Tên symbol để test (default: VIC)
    """
    
    print(f"📰 TESTING NEWS IMPORT FOR SYMBOL: {symbol_name}")
    print("=" * 60)
    
    from apps.stock.services.symbol_service import SymbolService
    from apps.stock.models import Symbol, Company, News
    
    # 1. Check if symbol exists in DB
    try:
        symbol = Symbol.objects.get(name=symbol_name)
        print(f"✅ Symbol found in DB: {symbol.name} (ID: {symbol.id})")
        
        if symbol.company:
            print(f"✅ Company linked: {symbol.company.company_name} (ID: {symbol.company.id})")
            
            # Check existing news
            existing_news = News.objects.filter(company=symbol.company)
            print(f"📊 Existing news count: {existing_news.count()}")
            
            if existing_news.exists():
                latest_news = existing_news.order_by('-public_date').first()
                print(f"📰 Latest news: {latest_news.title[:50]}...")
                print(f"   Published: {latest_news.public_date}")
        else:
            print("⚠️  No company linked to symbol")
            
    except Symbol.DoesNotExist:
        print(f"❌ Symbol {symbol_name} not found in DB")
        return
    
    print()
    
    # 2. Test fetching news data from VNStock
    print(f"🔍 FETCHING NEWS DATA FROM VNSTOCK...")
    
    try:
        service = SymbolService()
        
        # Use VNStock client directly to fetch news
        bundle, ok = service.vn_client.fetch_company_bundle_safe(symbol_name)
        
        if not ok or not bundle:
            print(f"❌ Failed to fetch bundle for {symbol_name}")
            return
            
        print(f"✅ Bundle fetched successfully")
        
        # Check news data in bundle
        news_df = bundle.get("news_df")
        if news_df is not None and not news_df.empty:
            print(f"📰 News data found: {len(news_df)} articles")
            print(f"   Columns: {list(news_df.columns)}")
            
            # Show sample news
            print(f"\n📋 Sample news titles:")
            for i, row in news_df.head(3).iterrows():
                title = row.get('title', 'No title')
                pub_date = row.get('public_date', 'No date')
                print(f"   {i+1}. {title[:60]}... ({pub_date})")
                
        else:
            print(f"❌ No news data in bundle for {symbol_name}")
            print(f"   Bundle keys: {list(bundle.keys())}")
            return
            
    except Exception as e:
        print(f"❌ Error fetching news data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # 3. Test news mapping
    print(f"🗂️  TESTING NEWS MAPPING...")
    
    try:
        from apps.stock.services.mappers import DataMappers
        
        mapped_news = DataMappers.map_news(news_df)
        print(f"✅ News mapped successfully: {len(mapped_news)} articles")
        
        # Show sample mapped data
        if mapped_news:
            sample = mapped_news[0]
            print(f"📋 Sample mapped news:")
            for key, value in sample.items():
                print(f"   {key}: {str(value)[:50]}...")
                
    except Exception as e:
        print(f"❌ Error mapping news: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # 4. Test news upsert
    print(f"💾 TESTING NEWS UPSERT...")
    
    try:
        from apps.stock.repositories import repositories as repo
        
        # Count before
        news_before = News.objects.filter(company=symbol.company).count()
        print(f"📊 News count before upsert: {news_before}")
        
        # Upsert news
        repo.upsert_news(symbol.company, mapped_news)
        
        # Count after
        news_after = News.objects.filter(company=symbol.company).count()
        print(f"📊 News count after upsert: {news_after}")
        print(f"📈 News added/updated: {news_after - news_before}")
        
        if news_after > news_before:
            print(f"✅ News upsert successful!")
            
            # Show latest news
            latest_news = News.objects.filter(company=symbol.company).order_by('-public_date')[:3]
            print(f"\n📰 Latest news in DB:")
            for news in latest_news:
                print(f"   • {news.title[:50]}... ({news.public_date})")
        else:
            print(f"⚠️  No new news added (possibly duplicates or mapping issue)")
            
    except Exception as e:
        print(f"❌ Error upserting news: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

def test_news_import_flow():
    """
    🔄 Test full news import flow
    
    CÁCH CHẠY:
        python tests/test_news_import.py
    
    MỤC ĐÍCH:
        - Test toàn bộ flow import news
        - Test với multiple symbols
        - Identify common issues
    """
    
    print("🔄 TESTING FULL NEWS IMPORT FLOW")
    print("=" * 80)
    
    # Test symbols - change these to symbols you have in your DB
    test_symbols = ['VIC', 'VNM', 'HPG', 'FPT', 'MSN']  # 🔄 Thay đổi symbols này
    
    for symbol_name in test_symbols:
        print(f"\n🧪 Testing symbol: {symbol_name}")
        print("-" * 40)
        
        try:
            test_symbol_news(symbol_name)
        except Exception as e:
            print(f"❌ Error testing {symbol_name}: {e}")
        
        print()
    
    print("✅ Full flow test completed!")
    print("=" * 80)

def check_news_statistics():
    """
    📊 Kiểm tra thống kê news trong database
    
    CÁCH CHẠY:
        python -c "from tests.test_news_import import check_news_statistics; check_news_statistics()"
    """
    
    print("📊 NEWS STATISTICS IN DATABASE")
    print("=" * 60)
    
    from apps.stock.models import Symbol, Company, News
    from django.db.models import Count
    
    # Overall stats
    total_symbols = Symbol.objects.count()
    symbols_with_company = Symbol.objects.filter(company__isnull=False).count()
    companies_with_news = Company.objects.filter(news__isnull=False).distinct().count()
    total_news = News.objects.count()
    
    print(f"📈 Overall Statistics:")
    print(f"   Total Symbols: {total_symbols}")
    print(f"   Symbols with Company: {symbols_with_company}")
    print(f"   Companies with News: {companies_with_news}")
    print(f"   Total News Articles: {total_news}")
    print()
    
    # Top companies by news count
    companies_by_news = (
        Company.objects
        .annotate(news_count=Count('news'))
        .filter(news_count__gt=0)
        .order_by('-news_count')[:10]
    )
    
    print(f"🏆 Top 10 Companies by News Count:")
    for i, company in enumerate(companies_by_news, 1):
        symbol_name = getattr(company.symbol_set.first(), 'name', 'Unknown') if company.symbol_set.exists() else 'Unknown'
        print(f"   {i:2d}. {company.company_name[:30]:<30} ({symbol_name}) - {company.news_count} articles")
    
    print()
    
    # Companies without news
    companies_without_news = Company.objects.filter(news__isnull=True).count()
    print(f"⚠️  Companies without news: {companies_without_news}")
    
    if companies_without_news > 0:
        print(f"📋 Sample companies without news:")
        sample_no_news = Company.objects.filter(news__isnull=True)[:5]
        for company in sample_no_news:
            symbol_name = getattr(company.symbol_set.first(), 'name', 'Unknown') if company.symbol_set.exists() else 'Unknown'
            print(f"   • {company.company_name} ({symbol_name})")
    
    print("=" * 60)

def fix_news_import_for_symbol(symbol_name):
    """
    🔧 Fix news import cho symbol cụ thể
    
    CÁCH CHẠY:
        python -c "from tests.test_news_import import fix_news_import_for_symbol; fix_news_import_for_symbol('VIC')"
    
    PARAMETERS:
        symbol_name (str): Symbol cần fix news import
    """
    
    print(f"🔧 FIXING NEWS IMPORT FOR {symbol_name}")
    print("=" * 60)
    
    from apps.stock.services.symbol_service import SymbolService
    from apps.stock.models import Symbol
    
    try:
        # Get symbol
        symbol = Symbol.objects.get(name=symbol_name)
        
        if not symbol.company:
            print(f"❌ Symbol {symbol_name} has no company linked")
            return
            
        # Initialize service
        service = SymbolService()
        
        # Fetch fresh data
        print(f"📡 Fetching fresh data for {symbol_name}...")
        bundle, ok = service.vn_client.fetch_company_bundle_safe(symbol_name)
        
        if not ok or not bundle:
            print(f"❌ Failed to fetch data for {symbol_name}")
            return
            
        # Process news specifically
        news_df = bundle.get("news_df")
        if news_df is not None and not news_df.empty:
            print(f"✅ News data available: {len(news_df)} articles")
            
            # Process news
            try:
                from apps.stock.services.company_processor import CompanyProcessor
                processor = CompanyProcessor()
                
                # Call the updated process_related_data
                processor.process_related_data(symbol.company, bundle)
                
                print(f"✅ News import completed for {symbol_name}")
                
                # Verify result
                from apps.stock.models import News
                news_count = News.objects.filter(company=symbol.company).count()
                print(f"📊 Total news for {symbol_name}: {news_count}")
                
            except Exception as e:
                print(f"❌ Error processing news: {e}")
                import traceback
                traceback.print_exc()
                
        else:
            print(f"❌ No news data available for {symbol_name}")
            
    except Symbol.DoesNotExist:
        print(f"❌ Symbol {symbol_name} not found")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == "__main__":
    print("📰 NEWS IMPORT TESTING SUITE")
    print("=" * 80)
    print()
    print("📋 Available Tests:")
    print("  1️⃣  test_symbol_news(symbol_name) - Test news import cho symbol cụ thể")
    print("  2️⃣  test_news_import_flow() - Test flow với multiple symbols")
    print("  3️⃣  check_news_statistics() - Xem thống kê news trong DB")
    print("  4️⃣  fix_news_import_for_symbol(symbol_name) - Fix import cho symbol")
    print()
    print("💡 Usage Examples:")
    print('   test_symbol_news("VIC")')
    print('   fix_news_import_for_symbol("VNM")')
    print()
    print("🚀 Running basic tests...")
    print()
    
    # Run basic tests
    check_news_statistics()
    print()
    test_symbol_news('VIC')  # Test với VIC symbol
    
    print()
    print("✅ Basic tests completed!")
    print("💡 Tip: Use fix_news_import_for_symbol() to fix specific symbols")
    print("=" * 80)