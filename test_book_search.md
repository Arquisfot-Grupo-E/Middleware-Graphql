# 🔍 **Pruebas del Buscador de Libros - BookWorm**

## 📋 **Prerequisitos**

Asegúrate de tener corriendo:
1. ✅ Back-reviews (Puerto 8000) 
2. ✅ Middleware GraphQL (Puerto 4000)

```powershell
# Verificar servicios
docker ps
# Deberías ver: fastapi_reviews_api, fastapi_reviews_db, graphql_gateway
```

---

## 🔍 **PARTE 1: Búsqueda SIN Autenticación**

### **Opción A: Directamente al servicio Reviews (FastAPI)**

```powershell
# Abrir la documentación de FastAPI
Start-Process "http://localhost:8000/docs"
```

**En Swagger UI:**
1. Expandir `GET /books/search`
2. Click en "Try it out"
3. En `q` escribir: `Harry Potter`
4. Click "Execute"

**O usando PowerShell:**
```powershell
# Buscar libros directamente en el servicio
$response = Invoke-RestMethod -Uri "http://localhost:8000/books/search?q=Harry Potter" -Method GET
$response | ConvertTo-Json -Depth 3
```

### **Opción B: A través del Middleware GraphQL**

```powershell
# Abrir GraphQL Playground
Start-Process "http://localhost:4000/graphql"
```

**En GraphQL Playground, ejecutar:**

```graphql
# Búsqueda básica de libros - NO requiere autenticación
query BuscarLibrosSinAuth {
  searchBooks(query: "Harry Potter") {
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

**Ejemplo con diferentes búsquedas:**

```graphql
# 1. Búsqueda por género
query BuscarCienciaFiccion {
  searchBooks(query: "science fiction") {
    id
    title
    authors
    categories
  }
}

# 2. Búsqueda por autor
query BuscarPorAutor {
  searchBooks(query: "Stephen King") {
    id
    title
    authors
    description
  }
}

# 3. Búsqueda específica
query BuscarLibroEspecifico {
  searchBooks(query: "1984 George Orwell") {
    id
    title
    authors
    description
    thumbnail
  }
}
```

**Resultado esperado:**
```json
{
  "data": {
    "searchBooks": [
      {
        "id": "google_book_id_123",
        "title": "Harry Potter and the Philosopher's Stone",
        "authors": ["J.K. Rowling"],
        "description": "The first book in the Harry Potter series...",
        "thumbnail": "https://books.google.com/books/content?id=...",
        "categories": ["Fantasy", "Fiction"],
        "publisher": "Bloomsbury",
        "published_date": "1997"
      }
    ]
  }
}
```

---

## 🔐 **PARTE 2: Funcionalidades CON Autenticación**

### **Paso 1: Registrar un usuario**

```graphql
mutation RegistrarUsuario {
  register(
    email: "test@bookworm.com"
    password: "password123"
    firstName: "Test"
    lastName: "User"
    description: "Amante de los libros"
  ) {
    id
    email
    first_name
    last_name
  }
}
```

### **Paso 2: Iniciar sesión**

```graphql
mutation IniciarSesion {
  login(
    email: "test@bookworm.com"
    password: "password123"
  ) {
    access
    refresh
  }
}
```

**🔑 IMPORTANTE:** Copia el token `access` del resultado.

### **Paso 3: Configurar autenticación en GraphQL Playground**

En la parte inferior del playground, busca "HTTP HEADERS" y agrega:

```json
{
  "Authorization": "Bearer TU_ACCESS_TOKEN_AQUI"
}
```

### **Paso 4: Obtener detalles de un libro específico (Con Auth)**

```graphql
query DetalleLibro {
  book(id: "ID_DEL_LIBRO_DE_LA_BUSQUEDA_ANTERIOR") {
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

### **Paso 5: Ver reseñas de un libro**

```graphql
query ReseñasDelLibro {
  reviewsForBook(bookId: "ID_DEL_LIBRO") {
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

### **Paso 6: Crear una reseña (Requiere Auth)**

```graphql
mutation CrearReseña {
  createReview(
    googleBookId: "ID_DEL_LIBRO"
    content: "Excelente libro, muy recomendado para amantes de la fantasía"
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

### **Paso 7: Ver mis reseñas (Requiere Auth)**

```graphql
query MisReseñas {
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

---

## 🧪 **PARTE 3: Pruebas de Integración Completas**

### **Flujo completo: Buscar → Ver → Reseñar**

```graphql
# 1. Buscar libros
query BuscarLibros {
  searchBooks(query: "The Lord of the Rings") {
    id
    title
    authors
  }
}

# 2. Ver detalles + reseñas existentes
query DetallesCompletos {
  book(id: "ID_OBTENIDO_ARRIBA") {
    id
    title
    authors
    description
    thumbnail
  }
  reviewsForBook(bookId: "ID_OBTENIDO_ARRIBA") {
    content
    rating
    user_id
  }
}

# 3. Crear mi reseña (con token de autenticación)
mutation MiReseña {
  createReview(
    googleBookId: "ID_OBTENIDO_ARRIBA"
    content: "Una obra maestra de la fantasía épica"
    rating: 5
  ) {
    id
    content
    rating
  }
}
```

---

## 🔍 **PARTE 4: Casos de Prueba Específicos**

### **Caso 1: Búsqueda que no encuentra resultados**

```graphql
query BusquedaVacia {
  searchBooks(query: "xyzabc123notfound") {
    id
    title
  }
}
```

**Resultado esperado:** Array vacío `[]`

### **Caso 2: Búsqueda con caracteres especiales**

```graphql
query BusquedaEspecial {
  searchBooks(query: "Don Quijote de la Mancha") {
    id
    title
    authors
  }
}
```

### **Caso 3: Libro que no existe**

```graphql
query LibroInexistente {
  book(id: "libro_que_no_existe_123") {
    id
    title
  }
}
```

**Resultado esperado:** `null`

### **Caso 4: Reseñas de libro sin reseñas**

```graphql
query LibroSinReseñas {
  reviewsForBook(bookId: "libro_sin_reseñas") {
    id
    content
  }
}
```

**Resultado esperado:** Array vacío `[]`

---

## 🚨 **Solución de Problemas**

### **❌ Error: "Connection refused"**

```powershell
# Verificar que el servicio esté corriendo
docker ps | findstr reviews

# Si no está, levantarlo:
cd "...\Back-reviews"
docker-compose up -d
```

### **❌ Error: "Unauthorized" (401)**

- Verificar que el token JWT esté en los headers
- Verificar que el token no haya expirado (duran 60 minutos)
- Re-hacer login para obtener nuevo token

### **❌ Error: "Book not found"**

- Usar IDs de libros que realmente existan en Google Books
- Los IDs cambian, usar siempre los obtenidos de `searchBooks`

### **❌ Error de CORS**

- El middleware ya tiene CORS configurado para `*`
- Verificar que estés accediendo desde el playground correcto

---

## 📊 **Métricas de Éxito**

### **✅ Búsqueda SIN Auth funciona si:**
- `searchBooks` devuelve resultados
- Los libros tienen `id`, `title`, `authors`
- No requiere headers de Authorization

### **✅ Funcionalidades CON Auth funcionan si:**
- `login` devuelve tokens `access` y `refresh`
- `myReviews` funciona con token válido
- `createReview` crea reseñas correctamente
- Error 401 cuando no hay token

### **✅ Integración completa funciona si:**
- Buscar → obtener ID → ver detalles → crear reseña
- El middleware comunica correctamente con el servicio
- Los datos son consistentes entre queries

---

## 🎯 **Siguientes Pasos**

Una vez que compruebes que el buscador funciona:

1. **Probar sistema de recomendaciones**
2. **Probar gestión de usuarios**
3. **Probar el frontend completo**
4. **Integración end-to-end**

¡Ejecuta estas pruebas paso a paso para verificar que todo funcione correctamente!