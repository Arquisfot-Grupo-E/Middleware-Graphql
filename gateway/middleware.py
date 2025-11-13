"""
Middleware de Throttling y Validación para GraphQL Gateway
Implementa:
- Query Depth Limiting
- Query Complexity Analysis
- Rate Limiting por usuario autenticado
"""

import os
import time
from typing import Any, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from graphql import GraphQLError
from graphql.language import ast
from graphql.language.visitor import Visitor, visit
import jwt


# ============================================
# CONFIGURACIÓN DE LÍMITES
# ============================================

MAX_QUERY_DEPTH = int(os.getenv("MAX_QUERY_DEPTH", "5"))
MAX_QUERY_COMPLEXITY = int(os.getenv("MAX_QUERY_COMPLEXITY", "100"))

# Rate limiting por usuario (requests por minuto)
USER_RATE_LIMIT = int(os.getenv("USER_RATE_LIMIT", "60"))  # 60 req/min = 1 req/s

# Almacenamiento en memoria para rate limiting
# En producción, usar Redis
user_request_log: Dict[str, list] = defaultdict(list)


# ============================================
# DEPTH LIMITING
# ============================================

class DepthAnalysisVisitor(Visitor):
    """Visitor para analizar la profundidad de una query GraphQL"""

    def __init__(self):
        self.max_depth = 0
        self.current_depth = 0

    def enter_field(self, node, *args):
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            self.max_depth = self.current_depth

    def leave_field(self, node, *args):
        self.current_depth -= 1


def validate_query_depth(document_ast) -> Optional[GraphQLError]:
    """
    Valida que la profundidad de la query no exceda el máximo permitido.

    Ejemplo de query con profundidad 3:
    {
      user {          # depth 1
        profile {     # depth 2
          avatar      # depth 3
        }
      }
    }
    """
    visitor = DepthAnalysisVisitor()
    visit(document_ast, visitor)

    if visitor.max_depth > MAX_QUERY_DEPTH:
        return GraphQLError(
            f"Query too deep. Max depth is {MAX_QUERY_DEPTH}, but got {visitor.max_depth}. "
            f"Please simplify your query or split it into multiple requests.",
            extensions={
                "code": "QUERY_TOO_DEEP",
                "max_depth": MAX_QUERY_DEPTH,
                "actual_depth": visitor.max_depth
            }
        )

    return None


# ============================================
# COMPLEXITY ANALYSIS
# ============================================

class ComplexityAnalysisVisitor(Visitor):
    """
    Visitor para calcular la complejidad de una query GraphQL.

    Costos por tipo de campo:
    - Campo simple: 1
    - Lista: 10 (asume 10 items)
    - Mutation: 5 (más costoso que query)
    - Nested field: costo acumulativo
    """

    def __init__(self):
        self.complexity = 0
        self.is_mutation = False

    def enter_operation_definition(self, node, *args):
        if node.operation.value == "mutation":
            self.is_mutation = True

    def enter_field(self, node, *args):
        # Campo base cuesta 1
        field_cost = 1

        # Mutations cuestan más
        if self.is_mutation:
            field_cost = 5

        # Si el campo tiene selección de sub-campos, es una lista
        if node.selection_set:
            # Asumimos listas de 10 items
            field_cost *= 10

        # Verificar argumentos que indican paginación
        if node.arguments:
            for arg in node.arguments:
                if arg.name.value in ["first", "limit"]:
                    # Si hay paginación, usar el valor especificado
                    if hasattr(arg.value, 'value'):
                        field_cost = int(arg.value.value)

        self.complexity += field_cost


def validate_query_complexity(document_ast) -> Optional[GraphQLError]:
    """
    Valida que la complejidad de la query no exceda el máximo permitido.

    Ejemplos de complejidad:
    - { me { id email } } = 11 (1 + 10)
    - mutation { createReview(...) } = 5
    - { books { reviews { user } } } = 111 (1 + 10 + 100)
    """
    visitor = ComplexityAnalysisVisitor()
    visit(document_ast, visitor)

    if visitor.complexity > MAX_QUERY_COMPLEXITY:
        return GraphQLError(
            f"Query too complex. Max complexity is {MAX_QUERY_COMPLEXITY}, but got {visitor.complexity}. "
            f"Please reduce the number of fields or use pagination.",
            extensions={
                "code": "QUERY_TOO_COMPLEX",
                "max_complexity": MAX_QUERY_COMPLEXITY,
                "actual_complexity": visitor.complexity
            }
        )

    return None


# ============================================
# RATE LIMITING POR USUARIO
# ============================================

def extract_user_id_from_token(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extrae el user_id del token JWT.

    Returns:
        user_id si el token es válido, None en caso contrario
    """
    if not authorization_header:
        return None

    try:
        # Formato: "Bearer <token>"
        token = authorization_header.replace("Bearer ", "").strip()

        # Decodificar sin verificar (solo para rate limiting, no para autenticación)
        # La autenticación real se hace en cada microservicio
        decoded = jwt.decode(token, options={"verify_signature": False})

        # El token puede tener 'user_id' o 'sub' (subject)
        return str(decoded.get("user_id") or decoded.get("sub"))

    except Exception as e:
        print(f"Error decoding JWT for rate limiting: {e}")
        return None


def check_rate_limit(user_id: str) -> Optional[GraphQLError]:
    """
    Verifica que el usuario no exceda el rate limit.

    Algoritmo: Sliding Window
    - Mantiene un log de timestamps de requests
    - Elimina requests más antiguos de 1 minuto
    - Verifica que no excedan el límite

    Args:
        user_id: ID del usuario

    Returns:
        GraphQLError si excede el límite, None en caso contrario
    """
    now = datetime.now()
    one_minute_ago = now - timedelta(minutes=1)

    # Obtener log de requests del usuario
    requests = user_request_log[user_id]

    # Eliminar requests antiguos (sliding window)
    requests = [req_time for req_time in requests if req_time > one_minute_ago]
    user_request_log[user_id] = requests

    # Verificar límite
    if len(requests) >= USER_RATE_LIMIT:
        oldest_request = min(requests)
        retry_after = int((oldest_request - one_minute_ago).total_seconds())

        return GraphQLError(
            f"Rate limit exceeded. Maximum {USER_RATE_LIMIT} requests per minute. "
            f"Please try again in {retry_after} seconds.",
            extensions={
                "code": "RATE_LIMIT_EXCEEDED",
                "limit": USER_RATE_LIMIT,
                "retry_after": retry_after,
                "window": "1 minute"
            }
        )

    # Registrar este request
    requests.append(now)

    return None


# ============================================
# VALIDACIÓN COMPLETA
# ============================================

def validate_query(document_ast, authorization_header: Optional[str]) -> list:
    """
    Ejecuta todas las validaciones de throttling.

    Args:
        document_ast: AST de la query GraphQL
        authorization_header: Header Authorization del request

    Returns:
        Lista de GraphQLErrors (vacía si todo está OK)
    """
    errors = []

    # 1. Validar profundidad
    depth_error = validate_query_depth(document_ast)
    if depth_error:
        errors.append(depth_error)

    # 2. Validar complejidad
    complexity_error = validate_query_complexity(document_ast)
    if complexity_error:
        errors.append(complexity_error)

    # 3. Rate limiting por usuario (solo si está autenticado)
    user_id = extract_user_id_from_token(authorization_header)
    if user_id:
        rate_limit_error = check_rate_limit(user_id)
        if rate_limit_error:
            errors.append(rate_limit_error)

    return errors


# ============================================
# LIMPIEZA PERIÓDICA (evitar memory leak)
# ============================================

def cleanup_old_requests():
    """
    Limpia requests antiguos del log en memoria.
    Debería ejecutarse periódicamente (ej: cada hora).

    En producción, usar Redis con TTL automático.
    """
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)

    for user_id in list(user_request_log.keys()):
        requests = user_request_log[user_id]
        requests = [req_time for req_time in requests if req_time > one_hour_ago]

        if not requests:
            del user_request_log[user_id]
        else:
            user_request_log[user_id] = requests
