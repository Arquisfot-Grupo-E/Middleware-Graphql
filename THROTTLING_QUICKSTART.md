# Throttling - Guía de Inicio Rápido

## 🚀 Instalación en 5 Minutos

### Paso 1: Instalar Dependencias

**GraphQL Gateway:**
```bash
cd middleware/Middleware-Graphql
pip install -r requirements.txt
```

**Reviews Service:**
```bash
cd backend/Back-reviews
pip install -r requirements.txt
```

### Paso 2: Configurar Variables de Entorno

**Opción A: Desarrollo (throttling desactivado)**
```bash
cd middleware/Middleware-Graphql
cp .env.development .env
```

**Opción B: Producción (throttling activado)**
```bash
cd middleware/Middleware-Graphql
cp .env.production .env
# Editar .env y cambiar contraseñas
```

### Paso 3: Reiniciar Servicios

```bash
cd middleware/Middleware-Graphql
docker-compose -f docker-compose.full.yml down
docker-compose -f docker-compose.full.yml up -d --build
```

### Paso 4: Verificar Funcionamiento

**Test 1: Health Check**
```bash
curl http://localhost:4000/health
```

Salida esperada:
```json
{
  "status": "healthy",
  "service": "graphql-gateway",
  "throttling_enabled": true
}
```

**Test 2: Query Simple**
```bash
curl https://localhost/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __typename }"}'
```

**Test 3: Rate Limiting**
```bash
# Ejecutar 100 requests rápidamente
for i in {1..100}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://localhost/graphql \
    -H "Content-Type: application/json" \
    -d '{"query": "{ __typename }"}' &
done
wait
```

Esperado: Algunos devuelven `429 Too Many Requests`

---

## ⚙️ Configuración Rápida

### Cambiar Límites

**Editar `.env`:**
```bash
# Throttling activado/desactivado
ENABLE_THROTTLING=true

# GraphQL
MAX_QUERY_DEPTH=5          # Profundidad máxima de queries
MAX_QUERY_COMPLEXITY=100   # Complejidad máxima
USER_RATE_LIMIT=60         # Requests por minuto por usuario

# Reiniciar
docker-compose restart
```

### Configuración por Ambiente

| Ambiente | ENABLE_THROTTLING | MAX_DEPTH | MAX_COMPLEXITY | RATE_LIMIT |
|----------|------------------|-----------|----------------|------------|
| Desarrollo | `false` | 10 | 500 | 1000 |
| Staging | `true` | 7 | 200 | 120 |
| Producción | `true` | 5 | 100 | 60 |

---

## 📊 Límites Implementados

### Nginx (Nivel 1)
- **Frontend**: 100 req/s con burst de 20
- **GraphQL API**: 30 req/s con burst de 10
- **Conexiones concurrentes**: 20 por IP

### GraphQL Gateway (Nivel 2)
- **Query Depth**: Máximo 5 niveles
- **Query Complexity**: Máximo 100 puntos
- **Rate Limit Usuario**: 60 req/min

### Reviews Service (Nivel 3)
- **POST /reviews/**: 10 req/min
- **GET /reviews/my-reviews**: 60 req/min
- **PATCH /reviews/{id}**: 20 req/min
- **DELETE /reviews/{id}**: 20 req/min
- **POST /reviews/{id}/vote**: 30 req/min
- **GET /reviews/book/{id}**: 100 req/min

---

## 🔧 Troubleshooting Rápido

### Problema: Requests rechazados en desarrollo

**Solución:**
```bash
# Desactivar throttling
echo "ENABLE_THROTTLING=false" >> .env
docker-compose restart
```

### Problema: Query rechazada por complejidad

**Solución 1: Simplificar query**
```graphql
# Usar paginación
{ books(limit: 10) { ... } }
```

**Solución 2: Aumentar límite**
```bash
# Solo en desarrollo
echo "MAX_QUERY_COMPLEXITY=500" >> .env
docker-compose restart
```

### Problema: No funciona rate limiting

**Verificar:**
```bash
# 1. Ver configuración
curl http://localhost:4000/

# 2. Ver logs
docker logs graphql_gateway_1

# 3. Verificar variable
docker exec graphql_gateway_1 env | grep THROTTLING
```

---

## 📚 Documentación Completa

Ver `THROTTLING.md` para documentación detallada:
- Arquitectura completa
- Tests exhaustivos
- Monitoreo
- Mejores prácticas

---

## 🆘 Soporte

**Logs en tiempo real:**
```bash
# Nginx
docker logs -f bookworm_nginx

# Gateway
docker logs -f graphql_gateway_1

# Reviews
docker logs -f bookworm_reviews
```

**Desactivar todo el throttling:**
```bash
# Gateway
echo "ENABLE_THROTTLING=false" > middleware/Middleware-Graphql/.env

# Reviews
echo "ENABLE_THROTTLING=false" > backend/Back-reviews/.env

# Reiniciar
docker-compose restart
```
