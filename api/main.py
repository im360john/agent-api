from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.routes.v1_router import v1_router
from api.settings import api_settings

# Try to import chat UI routes
try:
    from api.routes.chat_ui_fixed import chat_router
    CHAT_UI_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import fixed chat UI: {e}")
    try:
        from api.routes.chat_ui import chat_router
        CHAT_UI_AVAILABLE = True
    except Exception as e2:
        print(f"Warning: Could not import chat UI: {e2}")
        CHAT_UI_AVAILABLE = False

# Import test router
try:
    from api.routes.test_agent import test_router
    TEST_ROUTER_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import test router: {e}")
    TEST_ROUTER_AVAILABLE = False

# Import sessions router
try:
    from api.routes.chat_sessions import sessions_router
    SESSIONS_ROUTER_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import sessions router: {e}")
    SESSIONS_ROUTER_AVAILABLE = False

# Import simple fallback
try:
    from api.routes.chat_ui_simple import chat_router_simple
    SIMPLE_UI_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import simple chat UI: {e}")
    SIMPLE_UI_AVAILABLE = False


def create_app() -> FastAPI:
    """Create a FastAPI App"""

    # Create FastAPI App
    app: FastAPI = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        docs_url="/docs" if api_settings.docs_enabled else None,
        redoc_url="/redoc" if api_settings.docs_enabled else None,
        openapi_url="/openapi.json" if api_settings.docs_enabled else None,
    )

    # Add v1 router
    app.include_router(v1_router)
    
    # Add chat UI router if available
    if CHAT_UI_AVAILABLE:
        app.include_router(chat_router)
    elif SIMPLE_UI_AVAILABLE:
        # Use simple fallback
        app.include_router(chat_router_simple)
        print("Using simple chat UI fallback")
    
    # Add test router if available
    if TEST_ROUTER_AVAILABLE:
        app.include_router(test_router)
    
    # Add sessions router if available
    if SESSIONS_ROUTER_AVAILABLE:
        app.include_router(sessions_router)

    # Add Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create a FastAPI app
app = create_app()
