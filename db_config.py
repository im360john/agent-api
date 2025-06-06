import os

def get_db_url():
    # First, try to get the complete DATABASE_URL from Render
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        # Render provides PostgreSQL URLs in the format: postgres://...
        # SQLAlchemy 2.0+ requires postgresql:// or postgresql+psycopg://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    
    # Fallback to constructing from components
    db_user = os.getenv("DB_USER", "agno")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "agno")
    
    # Handle the 'None' string issue
    if db_port in ["None", "none", "", None]:
        db_port = "5432"
    
    # Validate port is numeric
    try:
        int(db_port)
    except ValueError:
        db_port = "5432"
    
    # Construct URL
    if db_password:
        return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        return f"postgresql+psycopg://{db_user}@{db_host}:{db_port}/{db_name}"

# Export the URL
DATABASE_URL = get_db_url()