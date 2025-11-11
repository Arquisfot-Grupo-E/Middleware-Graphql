# Integración del WAF en docker-compose.full.yml

## 📋 Resumen de Cambios

Se ha integrado exitosamente el **Web Application Firewall (WAF)** en el docker-compose completo del proyecto BookWorm. Ahora el sistema cuenta con protección de nivel empresarial contra ataques web.

---

## 🔄 Cambios Realizados

### 1. docker-compose.full.yml

Se reemplazaron los servicios Nginx básicos por servicios Nginx + ModSecurity WAF:

#### Antes:
```yaml
nginx-web:
  image: nginx:latest
  # Sin protección WAF
```

#### Después:
```yaml
nginx-web-waf:
  build:
    context: ../Frontend
    dockerfile: Dockerfile.nginx
  image: bookworm-nginx-waf:latest
  # Con ModSecurity 3 + OWASP CRS 4.0
```

### 2. Servicios WAF Agregados

**nginx-web-waf** (Puerto 443):
- Protege el frontend web React
- ModSecurity con reglas OWASP CRS
- Reglas personalizadas para GraphQL
- Rate limiting avanzado
- Logs en `Frontend/logs/`

**nginx-mobile-waf** (Puerto 8443):
- Protege la API móvil Flutter
- Misma protección que web
- Optimizado para tráfico móvil
- Logs en `Frontend-mobile/logs/`

---

## 🚀 Guía de Uso Completa

### Prerequisitos (Primera Vez)

```bash
# 1. Navegar al directorio del middleware
cd middleware/Middleware-Graphql

# 2. Crear redes Docker (si no existen)
bash scripts/setup-networks.sh

# 3. Setup del WAF
cd ../../front/Frontend
bash scripts/setup-waf.sh

# Esto creará:
# ✅ Directorios de logs
# ✅ Certificados SSL autofirmados
# ✅ Descarga unicode.mapping
# ✅ Construye imagen Docker con WAF
```

### Iniciar el Sistema Completo

```bash
# Volver al directorio del middleware
cd ../../middleware/Middleware-Graphql

# Levantar TODA la plataforma con WAF
docker-compose -f docker-compose.full.yml up --build

# En background (producción)
docker-compose -f docker-compose.full.yml up -d --build
```

### Verificar que Todo Funciona

```bash
# 1. Verificar que todos los contenedores están corriendo
docker-compose -f docker-compose.full.yml ps

# Deberías ver:
# ✅ bookworm_nginx_waf (WAF web - Puerto 443)
# ✅ bookworm_nginx_mobile_waf (WAF mobile - Puerto 8443)
# ✅ bookworm_frontend (React)
# ✅ graphql_gateway (GraphQL)
# ✅ bookworm_users (Django)
# ✅ bookworm_reviews (FastAPI)
# ✅ bookworm_recommendations (FastAPI)
# ✅ bookworm_scraping (Go)
# ✅ bookworm_postgres (PostgreSQL)
# ✅ bookworm_mongodb (MongoDB)
# ✅ bookworm_mysql (MySQL)
# ✅ bookworm_kafka (Kafka)

# 2. Test básico de conectividad
curl -k https://localhost/health
# Esperado: OK

# 3. Test de GraphQL
curl -k https://localhost/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{searchBooks(query:\"test\"){id title}}"}'

# 4. Test del WAF (SQL Injection - debe ser bloqueado)
curl -k "https://localhost/?id=1' OR '1'='1"
# Esperado: 403 Forbidden

# 5. Suite completa de tests del WAF
cd ../../front/Frontend
bash scripts/test-waf.sh https://localhost
# Esperado: 60+ tests passed
```

---

## 📊 Arquitectura Actualizada

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────┬─────────────────────┬──────────────────────┘
                 │ HTTPS :443          │ HTTPS :8443
                 ↓                     ↓
    ┌────────────────────┐  ┌────────────────────┐
    │ nginx-web-waf      │  │ nginx-mobile-waf   │  🛡️ WAF Layer
    │ ModSecurity 3      │  │ ModSecurity 3      │
    │ OWASP CRS 4.0      │  │ OWASP CRS 4.0      │
    └──────┬─────────────┘  └──────┬─────────────┘
           │                       │
           │ DMZ Network (172.20.0.0/24)
           ↓                       ↓
    ┌──────────────┐      ┌────────────────┐
    │ Frontend     │      │ GraphQL        │  🟢 DMZ
    │ React        │      │ Gateway        │
    └──────────────┘      └────┬───────────┘
                               │ Backend Network (172.21.0.0/24)
                               ↓
           ┌───────────────────┴────────────────────┐
           ↓                   ↓                     ↓
    ┌─────────────┐   ┌─────────────┐   ┌──────────────┐
    │ Back-users  │   │ Back-reviews│   │ Back-rec...  │  🟡 Backend
    │ (Django)    │   │ (FastAPI)   │   │ (FastAPI)    │
    └─────┬───────┘   └─────┬───────┘   └──────┬───────┘
          │                 │                   │
          │ Data Network (172.22.0.0/24)       │
          ↓                 ↓                   ↓
    ┌──────────┐   ┌──────────┐   ┌────────────────┐
    │PostgreSQL│   │ MongoDB  │   │ MySQL + Kafka  │  🔴 Data
    └──────────┘   └──────────┘   └────────────────┘
```

---

## 🔐 Protecciones Activas

### OWASP Top 10
✅ A01: Broken Access Control
✅ A02: Cryptographic Failures (TLS 1.2/1.3)
✅ A03: Injection (SQL, XSS, Command)
✅ A04: Insecure Design
✅ A05: Security Misconfiguration
✅ A06: Vulnerable Components
✅ A07: Authentication Failures
✅ A08: Data Integrity Failures
✅ A09: Logging Failures
✅ A10: SSRF

### GraphQL Específico
✅ Introspection blocking (`__schema`, `__type`)
✅ Query depth limiting (máximo 7 niveles)
✅ Batch query limiting (máximo 10 operaciones)
✅ Mutation authentication (JWT requerido)

### Rate Limiting
| Operación | Límite | Por |
|-----------|--------|-----|
| Login | 5 intentos | minuto/IP |
| Register | 3 intentos | hora/IP |
| GraphQL queries | 30 req | segundo/IP |
| General | 10 req | segundo/IP |
| Conexiones simultáneas | 10 | IP |

### Anti-Bot
✅ Blacklist de 30+ User-Agents maliciosos
✅ Detección de headless browsers
✅ Validación de headers HTTP estándar

---

## 📁 Estructura de Archivos

```
proyecto/
├── middleware/Middleware-Graphql/
│   ├── docker-compose.full.yml       ✨ ACTUALIZADO con WAF
│   ├── readme.md                     ✨ ACTUALIZADO con sección WAF
│   └── WAF_INTEGRATION.md            ✨ NUEVO (este documento)
│
├── front/Frontend/
│   ├── Dockerfile.nginx              ✨ Imagen Nginx + ModSecurity
│   ├── nginx-waf.conf               ✨ Config Nginx con WAF
│   ├── docker-compose-waf.yml       ✨ Compose standalone
│   ├── modsec/
│   │   ├── modsecurity.conf         ✨ Config ModSecurity
│   │   ├── custom-rules/            ✨ Reglas personalizadas
│   │   ├── blacklist-user-agents.txt
│   │   └── blacklist-ips.txt
│   ├── scripts/
│   │   ├── setup-waf.sh             ✨ Setup automático
│   │   ├── monitor-waf.sh           ✨ Monitoreo interactivo
│   │   └── test-waf.sh              ✨ Suite de tests
│   ├── logs/
│   │   ├── nginx/                   ✨ Logs Nginx
│   │   └── modsec/                  ✨ Logs ModSecurity
│   └── Documentación:
│       ├── WAF_README.md            ✨ Quick start
│       ├── WAF_DOCUMENTATION.md     ✨ Manual completo
│       ├── WAF_SUMMARY.md           ✨ Executive summary
│       ├── WAF_CHEATSHEET.md        ✨ Comandos rápidos
│       └── PRODUCTION_DEPLOYMENT.md ✨ Guía producción
│
└── front/Frontend-mobile/
    └── logs/                         ✨ Logs WAF mobile
        ├── nginx/
        └── modsec/
```

---

## 🔍 Monitoreo y Logs

### Dashboard Interactivo

```bash
cd front/Frontend
bash scripts/monitor-waf.sh

# Opciones disponibles:
# 1. Estadísticas en tiempo real
# 2. Últimas peticiones bloqueadas
# 3. Top IPs atacantes
# 4. Ataques por tipo
# 5. Logs en vivo
# 6. Estado del contenedor
```

### Logs Disponibles

**Web (Puerto 443):**
```bash
# Access logs
tail -f front/Frontend/logs/nginx/access.log

# WAF logs (con anomaly scores)
tail -f front/Frontend/logs/nginx/waf.log

# ModSecurity audit (peticiones bloqueadas)
tail -f front/Frontend/logs/modsec/audit.log

# Debug logs
tail -f front/Frontend/logs/modsec/debug.log
```

**Mobile (Puerto 8443):**
```bash
# Access logs
tail -f front/Frontend-mobile/logs/nginx/access.log

# ModSecurity audit
tail -f front/Frontend-mobile/logs/modsec/audit.log
```

### Consultas Útiles

```bash
# Ver ataques bloqueados hoy (web)
grep "$(date +%d/%b/%Y)" front/Frontend/logs/nginx/access.log | grep " 403 "

# Contar por tipo de ataque
grep -i "sql injection" front/Frontend/logs/modsec/audit.log | wc -l
grep -i "xss" front/Frontend/logs/modsec/audit.log | wc -l

# Top 10 IPs atacantes
awk '($9 == 403)' front/Frontend/logs/nginx/access.log | \
  awk '{print $1}' | sort | uniq -c | sort -rn | head -10
```

---

## 🛠️ Operaciones Comunes

### Detener el Sistema

```bash
cd middleware/Middleware-Graphql
docker-compose -f docker-compose.full.yml down
```

### Reiniciar Solo el WAF

```bash
# Web WAF
docker-compose -f docker-compose.full.yml restart nginx-web-waf

# Mobile WAF
docker-compose -f docker-compose.full.yml restart nginx-mobile-waf
```

### Ver Logs en Tiempo Real

```bash
# WAF web
docker-compose -f docker-compose.full.yml logs -f nginx-web-waf

# WAF mobile
docker-compose -f docker-compose.full.yml logs -f nginx-mobile-waf

# Todos los servicios
docker-compose -f docker-compose.full.yml logs -f
```

### Recargar Configuración (sin downtime)

```bash
# WAF web
docker exec bookworm_nginx_waf nginx -s reload

# WAF mobile
docker exec bookworm_nginx_mobile_waf nginx -s reload
```

### Ver Estado de Todos los Servicios

```bash
docker-compose -f docker-compose.full.yml ps
```

---

## 🚨 Troubleshooting

### Problema: WAF no inicia

```bash
# 1. Ver logs del contenedor
docker logs bookworm_nginx_waf

# 2. Verificar sintaxis de configuración
docker exec bookworm_nginx_waf nginx -t

# 3. Verificar que el archivo unicode.mapping existe
ls -la front/Frontend/modsec/unicode.mapping

# Si no existe:
cd front/Frontend
wget -O modsec/unicode.mapping \
  https://raw.githubusercontent.com/SpiderLabs/ModSecurity/v3/master/unicode.mapping
```

### Problema: Puerto 443 ocupado

```bash
# Ver qué está usando el puerto
sudo lsof -i :443

# Detener el servicio conflictivo o cambiar puerto en docker-compose.full.yml
```

### Problema: Falso positivo (bloqueo incorrecto)

```bash
# 1. Identificar la regla en logs
grep "403" front/Frontend/logs/nginx/access.log | tail -1
grep "id:" front/Frontend/logs/modsec/audit.log | tail -5

# 2. Deshabilitar temporalmente para testing
# En front/Frontend/modsec/modsecurity.conf agregar:
SecRule REQUEST_URI "@streq /api/endpoint" \
    "id:9999,phase:1,pass,ctl:ruleRemoveById=942100"

# 3. Recargar
docker exec bookworm_nginx_waf nginx -s reload
```

### Problema: No se pueden descargar dependencias

```bash
# Si estás detrás de un proxy corporativo o firewall:

# 1. Verificar conectividad
curl -I https://github.com

# 2. Construir imagen con cache de red del host
docker build --network=host -f front/Frontend/Dockerfile.nginx \
  -t bookworm-nginx-waf:latest front/Frontend/
```

---

## ✅ Checklist de Validación

Después de levantar el sistema, verificar:

- [ ] Todos los contenedores están corriendo (`docker-compose ps`)
- [ ] WAF web responde en puerto 443 (`curl -k https://localhost/health`)
- [ ] WAF mobile responde en puerto 8443 (`curl -k https://localhost:8443/health`)
- [ ] GraphQL funciona (`curl -k https://localhost/graphql`)
- [ ] SQL Injection es bloqueado (test con `curl`)
- [ ] Suite de tests pasa (`bash scripts/test-waf.sh`)
- [ ] Logs se están generando (`ls -la front/Frontend/logs/`)
- [ ] Dashboard de monitoreo funciona (`bash scripts/monitor-waf.sh`)

---

## 📚 Documentación Adicional

Para información más detallada, consultar:

1. **WAF_README.md** - Quick start y configuración básica (15 min)
2. **WAF_DOCUMENTATION.md** - Manual técnico completo (2-3 horas)
3. **WAF_SUMMARY.md** - Executive summary para presentaciones (30 min)
4. **WAF_CHEATSHEET.md** - Comandos de referencia rápida (5 min)
5. **PRODUCTION_DEPLOYMENT.md** - Guía para producción con SSL real (1 hora)

---

## 🎯 Próximos Pasos

### Para Desarrollo
1. ✅ Sistema funcionando con WAF
2. ✅ Familiarizarse con scripts de monitoreo
3. ✅ Revisar logs regularmente
4. ⏭️ Ajustar rate limits según necesidad
5. ⏭️ Agregar IPs/User-Agents a blacklists si es necesario

### Para Producción
1. ⏭️ Obtener certificados SSL válidos (Let's Encrypt)
2. ⏭️ Configurar DNS apuntando al servidor
3. ⏭️ Ajustar rate limits según tráfico real
4. ⏭️ Configurar backups automáticos de configuración
5. ⏭️ Configurar alertas por email para ataques masivos
6. ⏭️ Integrar con SIEM/Splunk/ELK (opcional)
7. ⏭️ Realizar penetration testing

---

**Última actualización**: 2024-11-10
**Versión**: 1.0
**Estado**: ✅ Integración completa y funcional
**Autor**: BookWorm Security Team
