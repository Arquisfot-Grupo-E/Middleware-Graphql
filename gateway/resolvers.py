import httpx
import os
from ariadne import QueryType, MutationType, make_executable_schema, load_schema_from_path
from dotenv import load_dotenv

load_dotenv()

# Cargar URLs de los servicios
USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")
REVIEWS_SERVICE_URL = os.getenv("REVIEWS_SERVICE_URL")

# Cargar el esquema desde el archivo
type_defs = load_schema_from_path("gateway/schema.graphql")

# Definir tipos de Query y Mutation
query = QueryType()
mutation = MutationType()

# --- Helpers ---

async def make_request(method: str, url: str, info=None, **kwargs):
    """Función helper para hacer peticiones a los microservicios."""
    headers = {}
    # Reenviar el token de autorización si existe
    if info and "request" in info.context:
        auth_header = info.context["request"].headers.get("authorization")
        if auth_header:
            headers["Authorization"] = auth_header

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, **kwargs)
        # Propagar errores de los servicios subyacentes
        response.raise_for_status()
        return response.json()

# --- Resolvers para Queries ---

@query.field("searchBooks")
async def resolve_search_books(_, info, query):
    url = f"{REVIEWS_SERVICE_URL}/books/search?q={query}"
    return await make_request("GET", url)

@query.field("book")
async def resolve_book(_, info, id):
    url = f"{REVIEWS_SERVICE_URL}/books/{id}"
    return await make_request("GET", url)

@query.field("reviewsForBook")
async def resolve_reviews_for_book(_, info, bookId):
    url = f"{REVIEWS_SERVICE_URL}/reviews/book/{bookId}"
    return await make_request("GET", url)

@query.field("myReviews")
async def resolve_my_reviews(_, info):
    # Esta ruta requiere autenticación, el token se reenvía automáticamente
    url = f"{REVIEWS_SERVICE_URL}/reviews/my-reviews"
    return await make_request("GET", url, info)

@query.field("me")
async def resolve_me(_, info):
    # Esta ruta requiere autenticación
    url = f"{USERS_SERVICE_URL}/api/accounts/profile/"
    return await make_request("GET", url, info)

# --- Resolvers para Mutaciones ---

@mutation.field("login")
async def resolve_login(_, info, email, password):
    url = f"{USERS_SERVICE_URL}/api/accounts/login/"
    payload = {"email": email, "password": password}
    return await make_request("POST", url, json=payload)

@mutation.field("register")
async def resolve_register(_, info, email, password, firstName, lastName):
    url = f"{USERS_SERVICE_URL}/api/accounts/register/"
    payload = {
        "email": email,
        "password": password,
        "first_name": firstName,
        "last_name": lastName,
    }
    return await make_request("POST", url, json=payload)

@mutation.field("createReview")
async def resolve_create_review(_, info, googleBookId, content, rating):
    url = f"{REVIEWS_SERVICE_URL}/reviews/"
    payload = {
        "google_book_id": googleBookId,
        "content": content,
        "rating": rating,
    }
    return await make_request("POST", url, info, json=payload)

@mutation.field("updateReview")
async def resolve_update_review(_, info, id, content=None, rating=None):
    url = f"{REVIEWS_SERVICE_URL}/reviews/{id}"
    payload = {}
    if content is not None:
        payload["content"] = content
    if rating is not None:
        payload["rating"] = rating
    return await make_request("PATCH", url, info, json=payload)

@mutation.field("deleteReview")
async def resolve_delete_review(_, info, id):
    url = f"{REVIEWS_SERVICE_URL}/reviews/{id}"
    return await make_request("DELETE", url, info)

# Crear el schema ejecutable
schema = make_executable_schema(type_defs, query, mutation)