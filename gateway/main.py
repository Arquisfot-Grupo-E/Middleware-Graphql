from fastapi import FastAPI
from ariadne.asgi import GraphQL
from .resolvers import schema
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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

# Crear la aplicación ASGI de GraphQL
graphql_app = GraphQL(schema, debug=True)

# Montar la aplicación GraphQL en la ruta /graphql
app.add_route("/graphql", graphql_app)

@app.get("/")
def read_root():
    return {"message": "GraphQL Gateway is running. Go to /graphql"}