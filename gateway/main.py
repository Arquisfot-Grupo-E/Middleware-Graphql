from fastapi import FastAPI
from ariadne.asgi import GraphQL
from .resolvers import schema

app = FastAPI()

# Crear la aplicación ASGI de GraphQL
graphql_app = GraphQL(schema, debug=True)

# Montar la aplicación GraphQL en la ruta /graphql
app.add_route("/graphql", graphql_app)

@app.get("/")
def read_root():
    return {"message": "GraphQL Gateway is running. Go to /graphql"}