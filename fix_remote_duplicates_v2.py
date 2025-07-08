#!/usr/bin/env python3
"""Fix duplicate brand names in remote database - handle conflicts"""

from sqlalchemy import create_engine, text

# External Render database URL
db_url = "postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"

engine = create_engine(db_url)

print("Analyzing and fixing duplicate products in remote database...\n")

with engine.begin() as conn:
    # First, let's see all the Wyld strawberry products
    print("=== Current Wyld Strawberry Products ===")
    result = conn.execute(text("""
        SELECT id, brand, name, created_at
        FROM pricing.products 
        WHERE LOWER(brand) = 'wyld' AND LOWER(name) LIKE '%strawberry%'
        ORDER BY created_at, id
    """))
    
    products = result.fetchall()
    for p in products:
        print(f"ID: {p[0]} - {p[1]} {p[2]} (created: {p[3]})")
    
    # Identify true duplicates (same product, different entries)
    print("\n=== Identifying True Duplicates ===")
    
    # Products to handle:
    # ID 2: "Wyld Strawberry Gummies" -> same as ID 1: "Strawberry Gummies"
    # ID 5: "Wyld Strawberry 20:1 CBD Hybrid Gummies" -> same as ID 4: "Strawberry 20:1 CBD Hybrid Gummies"
    
    duplicates_to_remove = [
        (2, 1, "Wyld Strawberry Gummies is duplicate of Strawberry Gummies"),
        (5, 4, "Wyld Strawberry 20:1 CBD Hybrid Gummies is duplicate of Strawberry 20:1 CBD Hybrid Gummies")
    ]
    
    for dup_id, keep_id, reason in duplicates_to_remove:
        print(f"\n{reason}")
        print(f"  - Will remove ID {dup_id} and keep ID {keep_id}")
        
        # First, update any price history to point to the correct product
        result = conn.execute(text("""
            UPDATE pricing.price_history 
            SET product_id = :keep_id 
            WHERE product_id = :dup_id
            RETURNING id
        """), {"keep_id": keep_id, "dup_id": dup_id})
        
        updated_count = result.rowcount
        print(f"  - Updated {updated_count} price history records")
        
        # Then delete the duplicate product
        conn.execute(text("DELETE FROM pricing.products WHERE id = :id"), {"id": dup_id})
        print(f"  - Deleted duplicate product ID {dup_id}")
    
    # Fix the Camino product name
    print("\n=== Fixing Camino Product ===")
    conn.execute(text("""
        UPDATE pricing.products 
        SET name = 'gummies' 
        WHERE id = 8 AND brand = 'Camino'
    """))
    print("✓ Fixed 'Camino Camino gummies' -> 'Camino gummies'")
    
    # Verify final state
    print("\n=== Final Product List ===")
    result = conn.execute(text("""
        SELECT id, brand, name 
        FROM pricing.products 
        ORDER BY brand, name
    """))
    
    for p in result:
        print(f"ID: {p[0]:3d} | {p[1]:15s} | {p[2]}")
        # Check if it would cause duplication
        if p[1].lower() in p[2].lower():
            print(f"        ⚠️  Still has brand in name!")
    
    # Test search queries
    print("\n=== Testing Search Queries ===")
    test_searches = [
        "wyld strawberry gummies",
        "strawberry gummies", 
        "strawberry 20:1 cbd",
        "camino gummies"
    ]
    
    for search in test_searches:
        print(f"\nSearching for: '{search}'")
        
        # Extract brand if present
        known_brands = ['wyld', 'kiva', 'camino', 'plus', 'wana', 'jetty', 'stiiizy']
        detected_brand = None
        search_term = search
        
        for brand in known_brands:
            if brand in search.lower():
                detected_brand = brand
                search_term = search.lower().replace(brand, '').strip()
                break
        
        # Search query
        query = "SELECT id, brand, name FROM pricing.products WHERE LOWER(name) LIKE :name"
        params = {"name": f"%{search_term}%"}
        
        if detected_brand:
            query += " AND LOWER(brand) = :brand"
            params["brand"] = detected_brand
        
        result = conn.execute(text(query), params)
        found = result.fetchall()
        
        print(f"  Detected brand: {detected_brand}")
        print(f"  Search term: {search_term}")
        print(f"  Found {len(found)} products:")
        for f in found:
            print(f"    - {f[1]} {f[2]}")

print("\n✓ All fixes applied successfully!")