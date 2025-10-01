import httpx
import os
from ariadne import QueryType, MutationType, make_executable_schema, load_schema_from_path
from dotenv import load_dotenv

load_dotenv()

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")
REVIEWS_SERVICE_URL = os.getenv("REVIEWS_SERVICE_URL")
RECOMMENDATIONS_SERVICE_URL = os.getenv("RECOMMENDATIONS_SERVICE_URL", "http://recommendations_service:8002")

type_defs = load_schema_from_path("gateway/schema.graphql")

query = QueryType()
mutation = MutationType()

async def make_request(method: str, url: str, info=None, **kwargs):
    """Función helper para hacer peticiones a los microservicios."""
    headers = {}
    if info and "request" in info.context:
        auth_header = info.context["request"].headers.get("authorization")
        if auth_header:
            headers["Authorization"] = auth_header

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

def normalize_review(review):
    """Normaliza una review de MongoDB para GraphQL"""
    if review and "_id" in review:
        review["id"] = review["_id"]
    return review

def normalize_reviews(reviews):
    """Normaliza una lista de reviews"""
    if reviews:
        return [normalize_review(review) for review in reviews]
    return reviews

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
    reviews = await make_request("GET", url)
    return normalize_reviews(reviews)

@query.field("myReviews")
async def resolve_my_reviews(_, info):
    url = f"{REVIEWS_SERVICE_URL}/reviews/my-reviews"
    reviews = await make_request("GET", url, info)
    return normalize_reviews(reviews)

@query.field("me")
async def resolve_me(_, info):
    url = f"{USERS_SERVICE_URL}/api/accounts/profile/"
    return await make_request("GET", url, info)

@query.field("recommendations")
async def resolve_recommendations(_, info, level=None):
    url = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/recommendations"
    if level:
        url += f"?level={level}"
    return await make_request("GET", url, info)

# --- Resolvers para Mutaciones ---

@mutation.field("login")
async def resolve_login(_, info, email, password):
    url = f"{USERS_SERVICE_URL}/api/accounts/login/"
    payload = {"email": email, "password": password}
    return await make_request("POST", url, json=payload)

@mutation.field("register")
async def resolve_register(_, info, email, password, firstName, lastName, description="None"):
    url = f"{USERS_SERVICE_URL}/api/accounts/register/"
    payload = {
        "email": email,
        "password": password,
        "first_name": firstName,
        "last_name": lastName,
        "description": description or ""
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
    result = await make_request("POST", url, info, json=payload)
    return normalize_review(result)

@mutation.field("updateReview")
async def resolve_update_review(_, info, id, content=None, rating=None):
    url = f"{REVIEWS_SERVICE_URL}/reviews/{id}"
    
    # Construir payload dinámicamente
    payload = {}
    if content is not None:
        payload["content"] = content
    if rating is not None:
        payload["rating"] = rating
    
    # Debug
    print(f"🔍 DEBUG updateReview:")
    print(f"   - id: {id}")
    print(f"   - content: {content}")
    print(f"   - rating: {rating}")
    print(f"   - payload: {payload}")
    
    # Validar que hay algo que actualizar
    if not payload:
        raise Exception("Debes proporcionar al menos content o rating")
    
    result = await make_request("PATCH", url, info, json=payload)
    return normalize_review(result)

@mutation.field("deleteReview")
async def resolve_delete_review(_, info, id):
    url = f"{REVIEWS_SERVICE_URL}/reviews/{id}"
    return await make_request("DELETE", url, info)

@mutation.field("saveGenres")
async def resolve_save_genres(_, info, genres):
    url_users = f"{USERS_SERVICE_URL}/api/accounts/profile/genres/"
    await make_request("POST", url_users, info, json={"preferred_genres": genres})
    
    url_recs = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/user/genres"
    result = await make_request("POST", url_recs, info, json={"genres": genres})
    
    return result

@mutation.field("searchBook")
async def resolve_search_book(_, info, bookId, title, authors=None, categories=None, publishedDate=None, description=None):
    url = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/user/search_book"
    
    payload = {
        "bookId": bookId,
        "title": title,
        "authors": authors or [],
        "categories": categories or [],
        "publishedDate": publishedDate or "",
        "description": description or ""
    }
    
    return await make_request("POST", url, info, json=payload)

schema = make_executable_schema(type_defs, query, mutation)