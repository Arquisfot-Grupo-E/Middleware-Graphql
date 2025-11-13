# Throttling Implementation - BookWorm

## Tabla de Contenidos
- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Arquitectura de Throttling](#arquitectura-de-throttling)
- [Niveles de Implementación](#niveles-de-implementación)
- [Configuración](#configuración)
- [Testing](#testing)
- [Monitoreo](#monitoreo)
- [Troubleshooting](#troubleshooting)

---

## Resumen Ejecutivo

Se ha implementado un sistema de **Throttling de 3 capas** para proteger la aplicación BookWorm contra:
- Ataques DDoS
- Queries GraphQL complejas que consuman demasiados recursos
- Abuso de endpoints por usuarios maliciosos
- Sobrecarga del sistema

### Beneficios
✅ **Seguridad**: Protección contra ataques de fuerza bruta y DDoS
✅ **Performance**: Previene queries que consuman demasiados recursos
✅ **Escalabilidad**: Control granular del tráfico por capa
✅ **Flexibilidad**: Configuración por ambiente (dev/prod)

---

## Arquitectura de Throttling

```
┌─────────────────────────────────────────────────┐
│         NIVEL 1: NGINX (Rate Limiting)          │
│  - 100 req/s: Frontend (estáticos)              │
│  - 30 req/s: GraphQL API                        │
│  - Burst control: Permite picos temporales      │
│  - Connection limiting: Max 20/50 concurrent    │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│    NIVEL 2: GRAPHQL GATEWAY (Query Analysis)    │
│  - Query Depth Limiting: Max 5 niveles          │
│  - Query Complexity Analysis: Max 100 puntos    │
│  - Rate Limiting por Usuario: 60 req/min        │
│  - Validación antes de ejecutar query           │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│  NIVEL 3: MICROSERVICIOS (Endpoint Specific)    │
│  Reviews Service:                                │
│  - POST /reviews/           : 10 req/min         │
│  - GET /reviews/my-reviews  : 60 req/min         │
│  - PATCH /reviews/{id}      : 20 req/min         │
│  - DELETE /reviews/{id}     : 20 req/min         │
│  - POST /reviews/{id}/vote  : 30 req/min         │
│  - GET /reviews/book/{id}   : 100 req/min        │
└─────────────────────────────────────────────────┘
```

---

## Niveles de Implementación

### Nivel 1: Nginx (Reverse Proxy)

**Archivo**: `/front/Frontend/nginx.conf`

**Características**:
- Rate limiting por IP usando `limit_req_zone`
- Connection limiting usando `limit_conn_zone`
- Burst control con `nodelay`
- Headers de respuesta `X-RateLimit-*`

**Configuración**:
```nginx
# Zona de rate limiting por IP
limit_req_zone $binary_remote_addr zone=graphql_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=frontend_limit:10m rate=100r/s;

# Límite de conexiones concurrentes
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# Aplicar en location
location /graphql {
  limit_req zone=graphql_limit burst=10 nodelay;
  limit_conn conn_limit 20;
  proxy_pass http://gateway;
}
```

**Respuesta en caso de rate limit excedido**:
```
HTTP/1.1 429 Too Many Requests
Content-Type: text/html
```

---

### Nivel 2: GraphQL Gateway

**Archivos**:
- `gateway/main.py` - Configuración principal
- `gateway/middleware.py` - Lógica de throttling
- `gateway/validation.py` - Validation rule de Ariadne

**Características**:
1. **Query Depth Limiting**: Previene queries infinitamente anidadas
2. **Query Complexity Analysis**: Calcula el costo de cada query
3. **Rate Limiting por Usuario**: Sliding window basado en JWT

#### Query Depth Limiting

Valida que la profundidad de anidamiento no exceda el límite.

**Ejemplo de query prohibida** (depth = 6):
```graphql
{
  user {                # depth 1
    profile {           # depth 2
      reviews {         # depth 3
        book {          # depth 4
          author {      # depth 5
            books {     # depth 6 ❌ EXCEDE LÍMITE (max 5)
```

**Respuesta de error**:
```json
{
  "errors": [{
    "message": "Query too deep. Max depth is 5, but got 6. Please simplify your query or split it into multiple requests.",
    "extensions": {
      "code": "QUERY_TOO_DEEP",
      "max_depth": 5,
      "actual_depth": 6
    }
  }]
}
```

#### Query Complexity Analysis

Calcula el "costo" de una query basado en:
- Campo simple: 1 punto
- Lista: 10 puntos (asume 10 items)
- Mutation: 5 puntos
- Nested fields: costo acumulativo

**Ejemplo de query costosa**:
```graphql
{
  books {              # 10 puntos (lista)
    reviews {          # 100 puntos (lista dentro de lista)
      user {           # 1000 puntos ❌ EXCEDE LÍMITE
```

**Complejidad total**: 1110 puntos (max: 100)

**Respuesta de error**:
```json
{
  "errors": [{
    "message": "Query too complex. Max complexity is 100, but got 1110. Please reduce the number of fields or use pagination.",
    "extensions": {
      "code": "QUERY_TOO_COMPLEX",
      "max_complexity": 100,
      "actual_complexity": 1110
    }
  }]
}
```

#### Rate Limiting por Usuario

Implementa un **sliding window** de 1 minuto por usuario autenticado.

**Algoritmo**:
1. Extrae `user_id` del token JWT
2. Mantiene log de timestamps de requests
3. Elimina requests más antiguos de 1 minuto
4. Verifica que no excedan el límite (60 req/min)

**Respuesta de error**:
```json
{
  "errors": [{
    "message": "Rate limit exceeded. Maximum 60 requests per minute. Please try again in 45 seconds.",
    "extensions": {
      "code": "RATE_LIMIT_EXCEEDED",
      "limit": 60,
      "retry_after": 45,
      "window": "1 minute"
    }
  }]
}
```

---

### Nivel 3: Microservicios (Reviews)

**Archivo**: `backend/Back-reviews/app/api/reviews.py`

**Tecnología**: SlowAPI (FastAPI rate limiting library)

**Límites por endpoint**:
| Endpoint | Método | Límite | Justificación |
|----------|--------|--------|---------------|
| `/reviews/` | POST | 10/min | Crear reseñas (escritura costosa) |
| `/reviews/my-reviews` | GET | 60/min | Lectura personal (común) |
| `/reviews/{id}` | PATCH | 20/min | Actualización (moderado) |
| `/reviews/{id}` | DELETE | 20/min | Eliminación (moderado) |
| `/reviews/{id}/vote` | POST | 30/min | Votos (prevenir spam) |
| `/reviews/book/{id}` | GET | 100/min | Lectura pública (muy común) |
| `/reviews/users/{id}` | GET | 60/min | Lectura de usuario (común) |

**Implementación**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/", response_model=ReviewOut)
@limiter.limit("10/minute")
def create_review(request: Request, ...):
    ...
```

**Respuesta de error**:
```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "error": "Rate limit exceeded: 10 per 1 minute"
}
```

---

## Configuración

### Variables de Entorno

#### GraphQL Gateway

**Archivo**: `.env` (copiar desde `.env.example`)

```bash
# Habilitar/deshabilitar throttling
ENABLE_THROTTLING=true

# Límites de queries GraphQL
MAX_QUERY_DEPTH=5
MAX_QUERY_COMPLEXITY=100

# Rate limiting por usuario (req/min)
USER_RATE_LIMIT=60
```

#### Reviews Service

**Archivo**: `backend/Back-reviews/.env`

```bash
# Habilitar/deshabilitar throttling
ENABLE_THROTTLING=true
```

### Configuración por Ambiente

#### Desarrollo (.env.development)
```bash
ENABLE_THROTTLING=false  # Desactivado para testing
MAX_QUERY_DEPTH=10
MAX_QUERY_COMPLEXITY=500
USER_RATE_LIMIT=1000
```

#### Producción (.env.production)
```bash
ENABLE_THROTTLING=true   # Activado para seguridad
MAX_QUERY_DEPTH=5
MAX_QUERY_COMPLEXITY=100
USER_RATE_LIMIT=60
```

### Cambiar Ambiente

**Opción 1: Copiar archivo**
```bash
# Desarrollo
cp .env.development .env

# Producción
cp .env.production .env
```

**Opción 2: Variable de entorno**
```bash
# Desarrollo
export ENABLE_THROTTLING=false

# Producción
export ENABLE_THROTTLING=true
```

---

## Testing

### 1. Test de Nginx Rate Limiting

**Test básico** (debe pasar):
```bash
curl -i https://localhost/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __typename }"}'
```

**Test de rate limit** (30 req/s):
```bash
# Ejecutar 100 requests en 1 segundo (debería fallar)
for i in {1..100}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://localhost/graphql &
done
wait
```

Esperado: Algunos requests devuelven `429 Too Many Requests`

---

### 2. Test de Query Depth Limiting

**Query válida** (depth 3, debe pasar):
```graphql
{
  me {
    email
    preferred_genres
  }
}
```

**Query prohibida** (depth 6, debe fallar):
```graphql
{
  me {
    profile {
      reviews {
        book {
          author {
            books {  # ❌ Depth = 6
              title
            }
          }
        }
      }
    }
  }
}
```

**Curl**:
```bash
curl https://localhost/graphql \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ me { profile { reviews { book { author { books { title } } } } } } }"
  }'
```

Esperado:
```json
{
  "errors": [{
    "message": "Query too deep. Max depth is 5, but got 6.",
    "extensions": {"code": "QUERY_TOO_DEEP"}
  }]
}
```

---

### 3. Test de Query Complexity

**Query simple** (complejidad ~11, debe pasar):
```graphql
{
  me {
    email
    first_name
  }
}
```

**Query compleja** (complejidad >100, debe fallar):
```graphql
{
  books {  # 10 puntos
    reviews {  # 100 puntos
      user {  # 1000 puntos ❌
        profile
      }
    }
  }
}
```

---

### 4. Test de Rate Limiting por Usuario

**Ejecutar 70 requests en 1 minuto** (límite: 60):
```bash
TOKEN="your_jwt_token_here"

for i in {1..70}; do
  curl -s -w "\n%{http_code}\n" https://localhost/graphql \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query": "{ me { email } }"}' &
done
wait
```

Esperado: Los primeros 60 pasan, del 61 al 70 devuelven error `RATE_LIMIT_EXCEEDED`

---

### 5. Test de Reviews Service Rate Limiting

**Test de crear reseñas** (límite: 10/min):
```bash
TOKEN="your_jwt_token_here"

for i in {1..15}; do
  curl -s -w "\n%{http_code}\n" http://localhost:8000/reviews/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "google_book_id": "test_'$i'",
      "content": "Test review",
      "rating": 5
    }'
done
```

Esperado: Los primeros 10 pasan, del 11 al 15 devuelven `429`

---

## Monitoreo

### 1. Logs de Nginx

**Ver rate limiting en tiempo real**:
```bash
docker logs -f bookworm_nginx 2>&1 | grep "limiting"
```

Salida esperada:
```
2024/11/12 18:30:00 [warn] 7#7: *123 limiting requests, excess: 10.500 by zone "graphql_limit", client: 172.20.0.5
```

### 2. Logs de GraphQL Gateway

**Ver validaciones de throttling**:
```bash
docker logs -f graphql_gateway_1 | grep -i "throttl\|rate\|depth\|complex"
```

### 3. Métricas Recomendadas

En producción, considerar implementar:

1. **Prometheus + Grafana**:
   - Rate de requests rechazados por throttling
   - Complejidad promedio de queries
   - Top usuarios por número de requests

2. **Alertas**:
   - Spike de requests rechazados (posible ataque)
   - Usuario excediendo rate limit frecuentemente
   - Queries con complejidad cerca del límite

### 4. Endpoint de Health Check

**Gateway**:
```bash
curl https://localhost/graphql-gateway-1:4000/health
```

Respuesta:
```json
{
  "status": "healthy",
  "service": "graphql-gateway",
  "throttling_enabled": true
}
```

**Reviews**:
```bash
curl http://localhost:8000/health
```

---

## Troubleshooting

### Problema: Todas las requests están siendo rechazadas

**Síntomas**:
```
429 Too Many Requests en todas las peticiones
```

**Soluciones**:

1. **Verificar configuración de Nginx**:
```bash
docker exec bookworm_nginx nginx -t
```

2. **Verificar límites**:
```bash
# Ver configuración actual
curl https://localhost:4000/
```

3. **Desactivar throttling temporalmente**:
```bash
# En .env
ENABLE_THROTTLING=false

# Reiniciar servicios
docker-compose restart
```

---

### Problema: Query válida siendo rechazada por complejidad

**Síntomas**:
```json
{
  "errors": [{
    "message": "Query too complex. Max complexity is 100, but got 110."
  }]
}
```

**Soluciones**:

1. **Optimizar la query** usando paginación:
```graphql
# Antes (complejidad alta)
{ books { reviews { ... } } }

# Después (con paginación)
{ books(limit: 10) { reviews(limit: 5) { ... } } }
```

2. **Aumentar límite temporalmente** (solo desarrollo):
```bash
# En .env
MAX_QUERY_COMPLEXITY=200
```

3. **Dividir en múltiples queries**:
```graphql
# Query 1
{ books { id title } }

# Query 2 (con IDs de query 1)
{ book(id: "123") { reviews { ... } } }
```

---

### Problema: Rate limiting no funciona para usuarios autenticados

**Síntomas**:
- Usuario excede límite pero no recibe error

**Causas posibles**:

1. **JWT no se está enviando**:
```bash
# Verificar header
curl -v https://localhost/graphql \
  -H "Authorization: Bearer YOUR_TOKEN"
```

2. **JWT inválido o expirado**:
```bash
# Verificar token
jwt decode YOUR_TOKEN
```

3. **Variable ENABLE_THROTTLING=false**:
```bash
# Verificar configuración
docker exec graphql_gateway_1 env | grep THROTTLING
```

---

### Problema: Desarrollo muy lento por throttling

**Solución recomendada**:

**Usar archivo .env.development**:
```bash
cp .env.development .env
docker-compose restart
```

O ajustar límites:
```bash
# En .env
ENABLE_THROTTLING=false  # Desactivar completamente
# O
USER_RATE_LIMIT=10000    # Límite muy alto
```

---

## Mejoras Futuras

### 1. Rate Limiting Distribuido con Redis

**Problema actual**: Rate limiting en memoria (no funciona con múltiples réplicas)

**Solución**:
```python
# Usar Redis en lugar de memoria
from slowapi.extension import RedisBackend

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379"
)
```

### 2. Rate Limiting Dinámico

**Concepto**: Ajustar límites basado en carga del sistema

```python
# Ejemplo pseudocódigo
if system_load > 80%:
    USER_RATE_LIMIT = 30  # Más restrictivo
else:
    USER_RATE_LIMIT = 60  # Normal
```

### 3. Whitelist de IPs Confiables

**Concepto**: Eximir de throttling a IPs específicas

```nginx
geo $limit {
    default 1;
    10.0.0.0/8 0;       # Red interna
    192.168.1.100 0;    # IP de testing
}

limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s if=$limit;
```

### 4. Tokens de Rate Limiting Premium

**Concepto**: Usuarios premium tienen límites más altos

```python
# Extraer tier del JWT
tier = jwt_payload.get("tier", "free")

if tier == "premium":
    rate_limit = 300  # req/min
elif tier == "business":
    rate_limit = 1000
else:
    rate_limit = 60
```

---

## Referencias

- [Nginx Rate Limiting](http://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [GraphQL Complexity Analysis](https://github.com/slicknode/graphql-query-complexity)
- [SlowAPI Documentation](https://slowapi.readthedocs.io/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)

---

## Autores

- **Implementación**: BookWorm Team
- **Fecha**: 2024-11-12
- **Versión**: 2.0.0
