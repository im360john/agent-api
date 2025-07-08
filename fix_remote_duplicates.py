#!/usr/bin/env python3
"""Fix duplicate brand names in remote database"""

from sqlalchemy import create_engine, text

# External Render database URL
db_url = "postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"

engine = create_engine(db_url)

print("Fixing duplicate brand names in remote database...\n")

with engine.begin() as conn:
    # Fix the duplicates
    fixes = [
        (8, 'gummies'),
        (5, 'Strawberry 20:1 CBD Hybrid Gummies'),
        (2, 'Strawberry Gummies')
    ]
    
    for product_id, new_name in fixes:
        # Get current name for logging
        result = conn.execute(text("SELECT brand, name FROM pricing.products WHERE id = :id"), {"id": product_id})
        row = result.fetchone()
        if row:
            old_full_name = f"{row[0]} {row[1]}"
            new_full_name = f"{row[0]} {new_name}"
            
            # Update the name
            conn.execute(text("UPDATE pricing.products SET name = :name WHERE id = :id"), 
                        {"name": new_name, "id": product_id})
            
            print(f"✓ Fixed ID {product_id}:")
            print(f"  OLD: {old_full_name}")
            print(f"  NEW: {new_full_name}")
    
    print("\n=== Verifying Fixes ===")
    
    # Check all products again
    result = conn.execute(text("""
        SELECT id, brand, name 
        FROM pricing.products 
        WHERE id IN (2, 5, 8)
        ORDER BY id
    """))
    
    print("\nUpdated products:")
    for p in result:
        print(f"ID: {p[0]} - {p[1]} {p[2]}")
    
    # Check for any remaining duplicates
    print("\n=== Checking for Remaining Duplicates ===")
    result = conn.execute(text("""
        SELECT id, brand, name 
        FROM pricing.products 
        WHERE LOWER(brand) = LOWER(SUBSTRING(name FROM 1 FOR LENGTH(brand)))
        ORDER BY brand, name
    """))
    
    duplicates = result.fetchall()
    if duplicates:
        print(f"⚠️  Still found {len(duplicates)} duplicates:")
        for p in duplicates:
            print(f"  ID: {p[0]} - {p[1]} {p[2]}")
    else:
        print("✓ No more duplicates found!")
    
    # Test search queries for Wyld strawberry products
    print("\n=== Testing Search Queries for Wyld Strawberry Products ===")
    result = conn.execute(text("""
        SELECT id, brand, name 
        FROM pricing.products 
        WHERE LOWER(brand) = 'wyld' AND LOWER(name) LIKE '%strawberry%'
        ORDER BY name
    """))
    
    for p in result:
        brand = p[1]
        name = p[2]
        # Apply the fix logic from the code
        if brand.lower() in name.lower():
            search_query = name
        else:
            search_query = f"{brand} {name}"
        print(f"ID: {p[0]} - {brand} {name}")
        print(f"  → Search query: '{search_query}'")

print("\n✓ All fixes applied successfully!")