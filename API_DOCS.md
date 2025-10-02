# 📚 Documentación de la API GraphQL

## 🌐 Endpoint
```
http://localhost:4000/graphql
```

## 🔐 Autenticación
La mayoría de las queries y mutations requieren autenticación mediante JWT. Incluye el token en el header:

```
Authorization: Bearer <tu_access_token>
```

---

## 📖 QUERIES

### 🔹 Servicio de Reseñas

#### 1. Buscar libros
```graphql
query SearchBooks {
  searchBooks(query: "Harry Potter") {
    id
    title
    authors
    description
    thumbnail
    categories
  }
}
```

#### 2. Obtener un libro específico
```graphql
query GetBook {
  book(id: "book_id_from_google") {
    id
    title
    authors
    description
    thumbnail
    categories
    publisher
    published_date
  }
}
```

#### 3. Ver reseñas de un libro
```graphql
query ReviewsForBook {
  reviewsForBook(bookId: "google_book_id") {
    id
    user_id
    content
    rating
    karma_score
    created_at
    updated_at
  }
}
```

#### 4. Ver mis reseñas
```graphql
query MyReviews {
  myReviews {
    id
    google_book_id
    content
    rating
    karma_score
    created_at
    updated_at
  }
}
```

### 🔹 Servicio de Usuarios

#### 5. Ver mi perfil
```graphql
query Me {
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

#### 6. Ver perfil público de otro usuario
```graphql
query UserProfile {
  userProfile(userId: 123) {
    id
    first_name
    last_name
    date_joined
    profile {
      avatar
      bio
    }
  }
}
```

### 🔹 Servicio de Recomendaciones

#### 7. Obtener recomendaciones generales
```graphql
# Sin nivel específico (devuelve todos los niveles)
query Recommendations {
  recommendations {
    bookId
    title
    authors
    categories
    avgRating
    nRatings
    reason
  }
}

# Con nivel específico (1, 2, o 3)
query RecommendationsLevel1 {
  recommendations(level: 1) {
    bookId
    title
    authors
    categories
    reason
  }
}
```

**Niveles de recomendación:**
- **Nivel 1**: Por géneros favoritos (gustos iniciales)
- **Nivel 2**: Por búsquedas anteriores
- **Nivel 3**: Por usuarios similares (filtrado colaborativo)

#### 8. Obtener recomendaciones colaborativas
```graphql
query CollaborativeRecs {
  collaborativeRecommendations {
    bookId
    title
    authors
    recommended_by_user
    because_both_rated_high
    similar_user_rating
    reason
  }
}
```

#### 9. Ver mis calificaciones
```graphql
query MyRatings {
  myRatings {
    bookId
    title
    authors
    stars
    timestamp
  }
}
```

---

## ✏️ MUTATIONS

### 🔹 Servicio de Usuarios

#### 1. Iniciar sesión
```graphql
mutation Login {
  login(email: "user@example.com", password: "password123") {
    access
    refresh
  }
}
```

#### 2. Registrarse
```graphql
mutation Register {
  register(
    email: "newuser@example.com"
    password: "securepass123"
    firstName: "John"
    lastName: "Doe"
    description: "Me encanta leer"
  ) {
    id
    email
    first_name
    last_name
  }
}
```

#### 3. Actualizar perfil
```graphql
mutation UpdateProfile {
  updateProfile(
    firstName: "Juan"
    lastName: "Pérez"
    avatar: "https://example.com/avatar.jpg"
    bio: "Amante de la literatura clásica"
  ) {
    user {
      id
      first_name
      last_name
    }
    avatar
    bio
  }
}
```

### 🔹 Servicio de Reseñas

#### 4. Crear reseña
```graphql
mutation CreateReview {
  createReview(
    googleBookId: "book_id_12345"
    content: "Excelente libro, muy recomendado!"
    rating: 5
  ) {
    id
    google_book_id
    content
    rating
    karma_score
    created_at
  }
}
```

#### 5. Actualizar reseña
```graphql
mutation UpdateReview {
  updateReview(
    id: "review_id_123"
    content: "Actualizando mi opinión..."
    rating: 4
  ) {
    id
    content
    rating
    updated_at
  }
}
```

#### 6. Eliminar reseña
```graphql
mutation DeleteReview {
  deleteReview(id: "review_id_123") {
    detail
  }
}
```

### 🔹 Servicio de Recomendaciones

#### 7. Guardar géneros favoritos (Nivel 1)
```graphql
mutation SaveGenres {
  saveGenres(genres: ["Fantasy", "Science Fiction", "Mystery"]) {
    user_id
    saved_genres
  }
}
```

**Importante:** Llamar esta mutation después del registro para activar las recomendaciones nivel 1.

#### 8. Registrar búsqueda de libro (Nivel 2)
```graphql
mutation SearchBook {
  searchBook(
    bookId: "google_book_id_123"
    title: "Harry Potter y la Piedra Filosofal"
    authors: ["J.K. Rowling"]
    categories: ["Fantasy", "Fiction"]
    publishedDate: "1997"
    description: "Un niño descubre que es un mago..."
  ) {
    user_id
    bookId
    title
    registered
  }
}
```

**Importante:** Llamar esta mutation cada vez que el usuario visualiza un libro para mejorar las recomendaciones nivel 2.

#### 9. Calificar libro (Nivel 3)
```graphql
mutation RateBook {
  rateBook(bookId: "google_book_id_123", stars: 5) {
    user_id
    bookId
    title
    stars
    timestamp
  }
}
```

**Importante:** Esta calificación es crucial para el filtrado colaborativo (nivel 3). Los usuarios con calificaciones similares recibirán recomendaciones compartidas.

#### 10. Confirmar preferencias
```graphql
mutation ConfirmPreferences {
  confirmPreferences {
    detail
  }
}
```

**Importante:** Llamar después de que el usuario selecciona sus géneros favoritos para marcar que completó el onboarding.

---

## 🔄 Flujo Completo de Usuario Nuevo

```graphql
# 1. Registrarse
mutation {
  register(
    email: "nuevo@example.com"
    password: "pass123"
    firstName: "Nuevo"
    lastName: "Usuario"
  ) {
    id
    email
  }
}

# 2. Iniciar sesión
mutation {
  login(email: "nuevo@example.com", password: "pass123") {
    access
    refresh
  }
}

# 3. Guardar géneros favoritos (activar recomendaciones nivel 1)
mutation {
  saveGenres(genres: ["Fantasy", "Science Fiction", "Romance"]) {
    saved_genres
  }
}

# 4. Confirmar que completó la selección de gustos
mutation {
  confirmPreferences {
    detail
  }
}

# 5. Ver recomendaciones iniciales
query {
  recommendations(level: 1) {
    title
    authors
    categories
  }
}

# 6. Buscar un libro que le interese
query {
  searchBooks(query: "lord of the rings") {
    id
    title
    authors
  }
}

# 7. Registrar que vio un libro (mejora recomendaciones nivel 2)
mutation {
  searchBook(
    bookId: "selected_book_id"
    title: "The Lord of the Rings"
    authors: ["J.R.R. Tolkien"]
    categories: ["Fantasy", "Adventure"]
  ) {
    registered
  }
}

# 8. Crear una reseña
mutation {
  createReview(
    googleBookId: "selected_book_id"
    content: "Obra maestra de la fantasía épica"
    rating: 5
  ) {
    id
    content
  }
}

# 9. Calificar el libro (activa recomendaciones nivel 3)
mutation {
  rateBook(bookId: "selected_book_id", stars: 5) {
    stars
  }
}

# 10. Ver recomendaciones colaborativas
query {
  collaborativeRecommendations {
    title
    recommended_by_user
    reason
  }
}
```

---

## 🐛 Manejo de Errores

Los errores se devuelven en este formato:
```json
{
  "errors": [
    {
      "message": "Error HTTP 401: Unauthorized",
      "path": ["myReviews"]
    }
  ]
}
```

Errores comunes:
- **401 Unauthorized**: Token JWT inválido o expirado
- **404 Not Found**: Recurso no encontrado
- **400 Bad Request**: Datos inválidos en la petición
- **500 Internal Server Error**: Error en el servidor

---

## 📝 Notas Importantes

1. **Tokens JWT**: Los tokens access tienen una duración de 60 minutos. Usa el refresh token para obtener uno nuevo.

2. **Sistema de 3 Niveles**:
   - El nivel 1 se activa cuando el usuario guarda sus géneros favoritos
   - El nivel 2 mejora conforme el usuario busca/visualiza libros
   - El nivel 3 se activa cuando el usuario califica libros con ≥4 estrellas

3. **IDs de libros**: Usa los IDs que devuelve Google Books API, no los IDs internos.

4. **Calificaciones**: Las estrellas van de 1 a 5. Calificaciones ≥4 se consideran positivas para el filtrado colaborativo.

5. **Géneros**: Deben ser exactamente 3 géneros cuando se guardan por primera vez.