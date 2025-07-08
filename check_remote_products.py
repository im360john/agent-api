#!/usr/bin/env python3
"""Check products in remote Render database"""

from sqlalchemy import create_engine, text

# External Render database URL
db_url = "postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"

engine = create_engine(db_url)

with engine.connect() as conn:
    print("=== Products in Remote Database ===")
    result = conn.execute(text("""
        SELECT id, brand, name 
        FROM pricing.products 
        ORDER BY brand, name
    """))
    
    products = result.fetchall()
    for p in products:
        print(f"ID: {p[0]:3d} | Brand: {p[1]:15s} | Name: {p[2]}")
    
    # Check for duplicates (products with brand name in the product name)
    print("\n=== Checking for Duplicate Brand Names ===")
    duplicates = []
    for p_id, brand, name in products:
        if brand.lower() in name.lower():
            duplicates.append((p_id, brand, name))
            print(f"⚠️  Duplicate found: ID {p_id} - '{brand} {name}' (brand already in name)")
    
    # Check Wyld strawberry products specifically
    print("\n=== Wyld Strawberry Products ===")
    result = conn.execute(text("""
        SELECT id, brand, name 
        FROM pricing.products 
        WHERE LOWER(brand) = 'wyld' AND LOWER(name) LIKE '%strawberry%'
        ORDER BY name
    """))
    
    wyld_products = result.fetchall()
    for p in wyld_products:
        print(f"ID: {p[0]} - {p[1]} {p[2]}")
        # Show what search query would be generated
        brand = p[1]
        name = p[2]
        if brand.lower() in name.lower():
            search_query = name
        else:
            search_query = f"{brand} {name}"
        print(f"  → Search query would be: '{search_query}'")
    
    # Check competitors
    print("\n=== Competitors ===")
    result = conn.execute(text("SELECT id, name, urls FROM pricing.competitors ORDER BY name"))
    for row in result:
        print(f"ID: {row[0]} - {row[1]}: {row[2]}")
    
    # Check latest price data
    print("\n=== Recent Price History (last 5) ===")
    result = conn.execute(text("""
        SELECT 
            p.brand || ' ' || p.name as product,
            c.name as competitor,
            ph.price,
            ph.availability_status,
            ph.scraped_at
        FROM pricing.price_history ph
        JOIN pricing.products p ON ph.product_id = p.id
        JOIN pricing.competitors c ON ph.competitor_id = c.id
        ORDER BY ph.scraped_at DESC
        LIMIT 5
    """))
    
    count = 0
    for row in result:
        count += 1
        print(f"{row[0]} at {row[1]}: ${row[2] if row[2] else 'N/A'} ({row[3]}) - {row[4]}")
    
    if count == 0:
        print("No price history found")
    
    # Clean up duplicates if user confirms
    if duplicates:
        print(f"\n=== Found {len(duplicates)} products with duplicate brand names ===")
        print("These products have the brand name already included in the product name.")
        print("This causes issues like 'Wyld Wyld Strawberry Gummies' when searching.")
        print("\nTo fix, we should remove the brand from the product name.")
        print("\nSQL to fix duplicates:")
        for p_id, brand, name in duplicates:
            # Remove brand from the beginning of name
            new_name = name
            if name.lower().startswith(brand.lower() + ' '):
                new_name = name[len(brand)+1:]
            print(f"UPDATE pricing.products SET name = '{new_name}' WHERE id = {p_id};")