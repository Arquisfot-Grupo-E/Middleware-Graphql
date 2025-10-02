# 🌐 Middleware GraphQL - BookWorm

Gateway GraphQL que unifica los tres microservicios del proyecto BookWorm: Usuarios, Reseñas y Recomendaciones.

## 🚀 Características

- **Unificación de APIs**: Un solo endpoint GraphQL para todos los servicios
- **Autenticación JWT**: Propagación automática de tokens de autenticación
- **Sistema de Recomendaciones de 3 Niveles**:
  - Nivel 1: Por géneros favoritos
  - Nivel 2: Por búsquedas/historial
  - Nivel 3: Filtrado colaborativo
- **Gestión completa de usuarios y perfiles**
- **CRUD de reseñas con sistema de karma**
- **Búsqueda de libros usando Google Books API**

## 📋 Requisitos Previos

- Docker y Docker Compose
- Los tres servicios backend ejecutándose:
  - `Back-users` (Django) en puerto 8001
  - `Back-reviews` (FastAPI) en puerto 8000
  - `Back-recommendations` (FastAPI) en puerto 8002

## 🛠️ Instalación y Configuración

### 1. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# El archivo ya viene configurado para Docker, pero puedes editarlo si es necesario
```

### 2. Levantar el middleware con Docker

```bash
# Desde el directorio del middleware
docker-compose up --build
```

El gateway estará disponible en: `http://localhost:4000/graphql`

### 3. Acceder al playground de GraphQL

Abre tu navegador en `http://localhost:4000/graphql` para acceder al playground interactivo.

## 🧪 Pruebas de Funcionamiento

### Paso 1: Verificar conexión básica

```graphql
query Health {
  searchBooks(query: "test") {
    id
    title
  }
}
```

### Paso 2: Probar el flujo de registro y autenticación

```graphql
# 1. Registrar nuevo usuario
mutation Register {
  register(
    email: "test@example.com"
    password: "testpass123"
    firstName: "Test"
    lastName: "User"
  ) {
    id
    email
  }
}

# 2. Iniciar sesión
mutation Login {
  login(email: "test@example.com", password: "testpass123") {
    access
    refresh
  }
}
```

**Importante**: Copia el token `access` para las siguientes peticiones.

### Paso 3: Configurar headers de autenticación

En el playground GraphQL, ve a "HTTP HEADERS" (abajo) y agrega:

```json
{
  "Authorization": "Bearer TU_ACCESS_TOKEN_AQUI"
}
```

### Paso 4: Probar el sistema de recomendaciones

```graphql
# 1. Guardar géneros favoritos (Nivel 1)
mutation SaveGenres {
  saveGenres(genres: ["Fantasy", "Science Fiction", "Mystery"]) {
    user_id
    saved_genres
  }
}

# 2. Confirmar preferencias
mutation Confirm {
  confirmPreferences {
    detail
  }
}

# 3. Ver recomendaciones nivel 1
query Recs1 {
  recommendations(level: 1) {
    title
    authors
    categories
    reason
  }
}

# 4. Buscar un libro
query Search {
  searchBooks(query: "Harry Potter") {
    id
    title
    authors
    categories
  }
}

# 5. Registrar que viste un libro (Nivel 2)
mutation RegisterSearch {
  searchBook(
    bookId: "ID_DEL_LIBRO_DE_ARRIBA"
    title: "Harry Potter y la Piedra Filosofal"
    authors: ["J.K. Rowling"]
    categories: ["Fantasy", "Fiction"]
  ) {
    registered
  }
}

# 6. Ver recomendaciones nivel 2
query Recs2 {
  recommendations(level: 2) {
    title
    authors
    reason
  }
}

# 7. Calificar un libro (Nivel 3)
mutation RateBook {
  rateBook(bookId: "ID_DEL_LIBRO", stars: 5) {
    stars
    timestamp
  }
}

# 8. Ver recomendaciones colaborativas
query CollabRecs {
  collaborativeRecommendations {
    title
    recommended_by_user
    reason
  }
}
```

### Paso 5: Probar el sistema de reseñas

```graphql
# 1. Crear reseña
mutation CreateReview {
  createReview(
    googleBookId: "ID_DEL_LIBRO"
    content: "Excelente libro, muy recomendado"
    rating: 5
  ) {
    id
    content
    rating
    karma_score
  }
}

# 2. Ver mis reseñas
query MyReviews {
  myReviews {
    id
    google_book_id
    content
    rating
    created_at
  }
}

# 3. Actualizar reseña
mutation UpdateReview {
  updateReview(
    id: "ID_DE_LA_RESEÑA"
    content: "Actualizando mi opinión"
    rating: 4
  ) {
    id
    content
    updated_at
  }
}

# 4. Ver reseñas de un libro
query BookReviews {
  reviewsForBook(bookId: "ID_DEL_LIBRO") {
    id
    user_id
    content
    rating
    karma_score
  }
}
```

## 🔍 Verificación de Integración

Para verificar que todos los servicios están correctamente integrados:

### 1. Verificar servicio de usuarios

```graphql
query TestUsers {
  me {
    user {
      id
      email
      first_name
      last_name
      has_selected_preferences
      preferred_genres
    }
    avatar
    bio
  }
}
```

**Resultado esperado**: Información del usuario autenticado.

### 2. Verificar servicio de reseñas

```graphql
query TestReviews {
  searchBooks(query: "1984") {
    id
    title
    authors
  }
}
```

**Resultado esperado**: Lista de libros de George Orwell.

### 3. Verificar servicio de recomendaciones

```graphql
query TestRecs {
  recommendations {
    title
    authors
    categories
  }
}
```

**Resultado esperado**: Lista de libros recomendados (puede estar vacía si es un usuario nuevo).

## 🐛 Solución de Problemas

### Error: "Connection refused"

**Problema**: El middleware no puede conectarse a uno de los servicios.

**Solución**:
1. Verifica que todos los servicios estén ejecutándose:
   ```bash
   docker ps
   ```
2. Verifica que los nombres de los contenedores coincidan con los del `.env`:
   - `django_users_service` (puerto 8001)
   - `fastapi_reviews_api` (puerto 8000)
   - `recommendations_service` (puerto 8002)

### Error: "Timeout al conectar con..."

**Problema**: El servicio está muy lento o no responde.

**Solución**:
1. Aumenta el timeout en `resolvers.py`:
   ```python
   async with httpx.AsyncClient(timeout=60.0) as client:
   ```
2. Verifica los logs del servicio problemático:
   ```bash
   docker logs [nombre_contenedor]
   ```

### Error: "401 Unauthorized"

**Problema**: Token JWT inválido o expirado.

**Solución**:
1. Obtén un nuevo token con la mutation `login`
2. Verifica que el header `Authorization` esté correctamente configurado
3. El formato debe ser: `Bearer <token>` (con espacio)

### Error: "No se encuentran recomendaciones"

**Problema**: El sistema no tiene suficiente información.

**Solución**:
1. Asegúrate de haber guardado géneros favoritos con `saveGenres`
2. Para nivel 2: registra búsquedas con `searchBook`
3. Para nivel 3: califica libros con `rateBook` (≥4 estrellas)

### El servicio funciona local pero no en Docker

**Problema**: URLs mal configuradas en `.env`.

**Solución**:
Usa los nombres de servicios de Docker, no localhost:
```bash
USERS_SERVICE_URL=http://django_users_service:8001
REVIEWS_SERVICE_URL=http://fastapi_reviews_api:8000
RECOMMENDATIONS_SERVICE_URL=http://recommendations_service:8002
```

## 📁 Estructura del Proyecto

```
Middleware-Graphql/
├── gateway/
│   ├── __init__.py
│   ├── main.py              # Aplicación FastAPI
│   ├── resolvers.py         # Resolvers GraphQL
│   └── schema.graphql       # Definición del schema
├── .env                     # Variables de entorno
├── .env.example            # Ejemplo de configuración
├── docker-compose.yml      # Configuración Docker
├── Dockerfile              # Imagen del gateway
├── requirements.txt        # Dependencias Python
├── README.md              # Este archivo
└── API_DOCUMENTATION.md   # Documentación completa de la API
```

## 📚 Documentación Adicional

Para ver ejemplos detallados de todas las queries y mutations disponibles, consulta:
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)**: Documentación completa con ejemplos

## 🔗 URLs de los Servicios

- **Gateway GraphQL**: http://localhost:4000/graphql
- **Servicio de Usuarios**: http://localhost:8001
- **Servicio de Reseñas**: http://localhost:8000
- **Servicio de Recomendaciones**: http://localhost:8002

## 🛡️ Seguridad

- Los tokens JWT expiran después de 60 minutos
- Usa el `refresh` token para obtener nuevos access tokens
- Nunca compartas tus tokens en repositorios públicos
- En producción, usa HTTPS para todas las comunicaciones

## 📝 Notas Importantes

1. **Sistema de 3 Niveles**: Los niveles de recomendación se activan progresivamente:
   - Nivel 1: Inmediato al guardar géneros
   - Nivel 2: Mejora con cada búsqueda registrada
   - Nivel 3: Requiere múltiples usuarios calificando libros

2. **IDs de libros**: Usa siempre los IDs de Google Books, no los IDs internos de MongoDB.

3. **Calificaciones vs Reseñas**:
   - Calificaciones (1-5 estrellas): Para recomendaciones
   - Reseñas: Texto + calificación + karma

4. **Orden de operaciones**: Para mejores resultados:
   1. Registrarse
   2. Guardar géneros
   3. Confirmar preferencias
   4. Buscar y ver libros
   5. Calificar libros
   6. Crear reseñas

## 🤝 Contribución

Para contribuir al proyecto:
1. Realiza cambios en una rama separada
2. Prueba todos los flujos de queries y mutations
3. Actualiza la documentación si es necesario
4. Crea un pull request con descripción detallada

## 📄 Licencia

GPL-3.0 License - Ver archivo [LICENSE](LICENSE) para más detalles.