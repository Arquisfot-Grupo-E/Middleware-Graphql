from fastapi import FastAPI, Request
from ariadne.asgi import GraphQL
from .resolvers import schema
from .validation import ThrottlingValidationRule
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="BookWorm GraphQL Gateway",
    description="GraphQL Gateway with Throttling and Rate Limiting",
    version="2.0.0"
)

# Define allowed origins for CORS
origins = [
    "*"
]

# Add CORS middleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# ============================================
# THROTTLING CONFIGURATION
# ============================================

# Leer configuración desde variables de entorno
MAX_QUERY_DEPTH = int(os.getenv("MAX_QUERY_DEPTH", "5"))
MAX_QUERY_COMPLEXITY = int(os.getenv("MAX_QUERY_COMPLEXITY", "100"))
USER_RATE_LIMIT = int(os.getenv("USER_RATE_LIMIT", "60"))
ENABLE_THROTTLING = os.getenv("ENABLE_THROTTLING", "true").lower() == "true"

# Crear la aplicación ASGI de GraphQL con validación de throttling
if ENABLE_THROTTLING:
    graphql_app = GraphQL(
        schema,
        debug=True,
        validation_rules=[ThrottlingValidationRule]  # Agregar validación de throttling
    )
else:
    # Sin throttling (para desarrollo)
    graphql_app = GraphQL(schema, debug=True)

# Montar la aplicación GraphQL en la ruta /graphql
app.add_route("/graphql", graphql_app)


@app.get("/")
def read_root():
    """Root endpoint con información del gateway"""
    return {
        "message": "GraphQL Gateway is running. Go to /graphql",
        "version": "2.0.0",
        "throttling": {
            "enabled": ENABLE_THROTTLING,
            "max_query_depth": MAX_QUERY_DEPTH,
            "max_query_complexity": MAX_QUERY_COMPLEXITY,
            "user_rate_limit": f"{USER_RATE_LIMIT} req/min"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint para monitoreo"""
    return {
        "status": "healthy",
        "service": "graphql-gateway",
        "throttling_enabled": ENABLE_THROTTLING
    }