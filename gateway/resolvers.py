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

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.ReadTimeout:
            raise Exception(f"Timeout al conectar con {url}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Error HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise Exception(f"Error en la petición: {str(e)}")

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

# ============================================
# QUERIES - SERVICIO DE RESEÑAS
# ============================================

@query.field("searchBooks")
async def resolve_search_books(_, info, query):
    url = f"{REVIEWS_SERVICE_URL}/books/search?q={query}"
    return await make_request("GET", url)

@query.field("book")
async def resolve_book(_, info, id):
    url = f"{REVIEWS_SERVICE_URL}/books/id/{id}"
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

# ============================================
# QUERIES - SERVICIO DE USUARIOS
# ============================================

@query.field("me")
async def resolve_me(_, info):
    url = f"{USERS_SERVICE_URL}/api/accounts/profile/"
    return await make_request("GET", url, info)

@query.field("userProfile")
async def resolve_user_profile(_, info, userId):
    """Obtiene el perfil público de un usuario específico"""
    url = f"{USERS_SERVICE_URL}/api/accounts/users/{userId}/profile/"
    return await make_request("GET", url, info)

# ============================================
# QUERIES - SERVICIO DE RECOMENDACIONES
# ============================================

@query.field("recommendations")
async def resolve_recommendations(_, info, level=None):
    """
    Obtiene recomendaciones generales del usuario.
    level: Nivel de recomendación (1, 2, o 3). Si no se especifica, devuelve todos los niveles.
    """
    url = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/user/recommendations"
    if level:
        url += f"?level={level}"
    return await make_request("GET", url, info)

@query.field("collaborativeRecommendations")
async def resolve_collaborative_recommendations(_, info):
    """
    Obtiene recomendaciones basadas en filtrado colaborativo (Nivel 3).
    """
    url = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/user/recommendations/collaborative"
    
    try:
        result = await make_request("GET", url, info)
        
        # Si el resultado no es una lista, devolver lista vacía
        if not isinstance(result, list):
            # Puede venir en formato {"recommendations": [...]}
            if isinstance(result, dict) and "recommendations" in result:
                return result["recommendations"]
            return []
        
        return result
    except Exception as e:
        # En caso de error, devolver lista vacía en lugar de error
        print(f"Warning: Error getting collaborative recommendations: {e}")
        return []

@query.field("myRatings")
async def resolve_my_ratings(_, info):
    """Obtiene todas las calificaciones del usuario actual"""
    url = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/user/ratings"
    return await make_request("GET", url, info)

# ============================================
# MUTATIONS - SERVICIO DE USUARIOS
# ============================================

@mutation.field("login")
async def resolve_login(_, info, email, password):
    url = f"{USERS_SERVICE_URL}/api/accounts/login/"
    payload = {"email": email, "password": password}
    return await make_request("POST", url, json=payload)

@mutation.field("register")
async def resolve_register(_, info, email, password, firstName, lastName, description=None):
    url = f"{USERS_SERVICE_URL}/api/accounts/register/"
    payload = {
        "email": email,
        "password": password,
        "first_name": firstName,
        "last_name": lastName,
        "description": description or ""
    }
    return await make_request("POST", url, json=payload)

@mutation.field("updateProfile")
async def resolve_update_profile(_, info, firstName=None, lastName=None, avatar=None, bio=None):
    """Actualiza el perfil del usuario actual"""
    url = f"{USERS_SERVICE_URL}/api/accounts/profile/update/"
    
    payload = {}
    if firstName is not None:
        payload["first_name"] = firstName
    if lastName is not None:
        payload["last_name"] = lastName
    if avatar is not None:
        payload["avatar"] = avatar
    if bio is not None:
        payload["bio"] = bio
    
    if not payload:
        raise Exception("Debes proporcionar al menos un campo para actualizar")
    
    return await make_request("PUT", url, info, json=payload)

# ============================================
# MUTATIONS - SERVICIO DE RESEÑAS
# ============================================

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
    
    payload = {}
    if content is not None:
        payload["content"] = content
    if rating is not None:
        payload["rating"] = rating
    
    if not payload:
        raise Exception("Debes proporcionar al menos content o rating")
    
    result = await make_request("PATCH", url, info, json=payload)
    return normalize_review(result)

@mutation.field("deleteReview")
async def resolve_delete_review(_, info, id):
    url = f"{REVIEWS_SERVICE_URL}/reviews/{id}"
    return await make_request("DELETE", url, info)

# ============================================
# MUTATIONS - SERVICIO DE RECOMENDACIONES
# ============================================

@mutation.field("saveGenres")
async def resolve_save_genres(_, info, genres):
    """
    Guarda los géneros preferidos del usuario en ambos servicios:
    1. Servicio de usuarios (para el perfil)
    2. Servicio de recomendaciones (para el algoritmo)
    """
    # Primero guardar en el servicio de usuarios
    url_users = f"{USERS_SERVICE_URL}/api/accounts/profile/genres/"
    await make_request("POST", url_users, info, json={"preferred_genres": genres})
    
    # Luego guardar en el servicio de recomendaciones
    url_recs = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/user/genres"
    result = await make_request("POST", url_recs, info, json={"genres": genres})
    
    return result

@mutation.field("searchBook")
async def resolve_search_book(_, info, bookId, title, authors=None, categories=None, publishedDate=None, description=None):
    """
    Registra que el usuario ha buscado/visto un libro específico.
    Esto se usa para el nivel 2 de recomendaciones (basadas en búsquedas).
    """
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

@mutation.field("rateBook")
async def resolve_rate_book(_, info, bookId, stars):
    """
    Permite al usuario calificar un libro con estrellas (1-5).
    Esta calificación se usa para el nivel 3 de recomendaciones (filtrado colaborativo).
    """
    url = f"{RECOMMENDATIONS_SERVICE_URL}/api/v1/user/rate_book"
    
    payload = {
        "bookId": bookId,
        "stars": stars
    }
    
    try:
        result = await make_request("POST", url, info, json=payload)
        # Asegurar que los campos opcionales existan
        return {
            "user_id": result.get("user_id"),
            "bookId": result.get("bookId"),
            "title": result.get("title") or f"Book {bookId}",
            "authors": result.get("authors") or [],
            "stars": result.get("stars"),
            "timestamp": result.get("timestamp"),
            "message": result.get("message", "Rating saved successfully")
        }
    except Exception as e:
        # Si falla, devolver información básica
        raise Exception(f"Error al calificar el libro: {str(e)}")

@mutation.field("confirmPreferences")
async def resolve_confirm_preferences(_, info):
    """
    Confirma que el usuario ya seleccionó sus gustos iniciales.
    Se llama después de que el usuario escoge sus géneros favoritos.
    """
    url = f"{USERS_SERVICE_URL}/api/accounts/confirm-preferences/"
    return await make_request("POST", url, info)

# ============================================
# CREACIÓN DEL SCHEMA
# ============================================

schema = make_executable_schema(type_defs, query, mutation)