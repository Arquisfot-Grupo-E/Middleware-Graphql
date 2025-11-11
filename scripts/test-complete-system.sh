#!/bin/bash
# ================================
# Test Completo del Sistema BookWorm
# ================================
# Script automatizado para probar toda la implementación

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Contadores
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║ $(printf '%-56s' "$1") ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_phase() {
    echo ""
    echo -e "${BLUE}═══ FASE $1: $2 ═══${NC}"
    echo ""
}

print_test() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -ne "${YELLOW}[TEST $TESTS_TOTAL]${NC} $1 ... "
}

print_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "${GREEN}✓ PASS${NC}"
}

print_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "${RED}✗ FAIL${NC}"
    if [ ! -z "$1" ]; then
        echo -e "${RED}  Error: $1${NC}"
    fi
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Banner
clear
echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     BOOKWORM - TEST COMPLETO DEL SISTEMA CON WAF        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo "Fecha: $(date)"
echo "Usuario: $(whoami)"
echo ""

# ================================
# FASE 1: Verificación de Prerequisitos
# ================================
print_phase 1 "Verificación de Prerequisitos"

print_test "Docker instalado"
if command -v docker &> /dev/null; then
    print_pass
else
    print_fail "Docker no está instalado"
    exit 1
fi

print_test "Docker Compose instalado"
if docker compose version &> /dev/null || command -v docker-compose &> /dev/null; then
    print_pass
else
    print_fail "Docker Compose no está instalado"
    exit 1
fi

print_test "Redes Docker creadas"
if docker network inspect dmz_network &> /dev/null && \
   docker network inspect backend_network &> /dev/null && \
   docker network inspect data_network &> /dev/null; then
    print_pass
else
    print_fail "Redes no creadas. Ejecutar: bash scripts/setup-networks.sh"
    exit 1
fi

# ================================
# FASE 2: Verificación de Contenedores
# ================================
print_phase 2 "Verificación de Contenedores"

required_containers=(
    "bookworm_nginx_waf"
    "bookworm_frontend"
    "graphql_gateway"
    "bookworm_users"
    "bookworm_reviews"
    "bookworm_recommendations"
    "bookworm_postgres"
    "bookworm_mongodb"
)

for container in "${required_containers[@]}"; do
    print_test "Contenedor $container corriendo"
    if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
        print_pass
    else
        print_fail "Contenedor no está corriendo"
        echo -e "${RED}  Ejecutar: docker-compose -f docker-compose.full.yml up -d${NC}"
    fi
done

# ================================
# FASE 3: Tests de Conectividad Básica
# ================================
print_phase 3 "Tests de Conectividad Básica"

print_test "WAF Web Health Check (Puerto 443)"
status=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/health 2>/dev/null || echo "000")
if [ "$status" = "200" ]; then
    print_pass
else
    print_fail "Esperado 200, obtenido $status"
fi

print_test "Frontend accesible"
status=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/ 2>/dev/null || echo "000")
if [ "$status" = "200" ]; then
    print_pass
else
    print_fail "Esperado 200, obtenido $status"
fi

print_test "GraphQL Gateway accesible"
status=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/graphql 2>/dev/null || echo "000")
if [ "$status" != "000" ]; then
    print_pass
else
    print_fail "GraphQL no responde"
fi

# ================================
# FASE 4: Tests del WAF
# ================================
print_phase 4 "Tests de Protección WAF"

print_test "SQL Injection bloqueado"
status=$(curl -k -s -o /dev/null -w "%{http_code}" "https://localhost/?id=1' OR '1'='1" 2>/dev/null || echo "000")
if [ "$status" = "403" ]; then
    print_pass
else
    print_fail "Esperado 403, obtenido $status"
fi

print_test "XSS bloqueado"
status=$(curl -k -s -o /dev/null -w "%{http_code}" "https://localhost/?name=<script>alert(1)</script>" 2>/dev/null || echo "000")
if [ "$status" = "403" ]; then
    print_pass
else
    print_fail "Esperado 403, obtenido $status"
fi

print_test "Path Traversal bloqueado"
status=$(curl -k -s -o /dev/null -w "%{http_code}" "https://localhost/../../../etc/passwd" 2>/dev/null || echo "000")
if [ "$status" = "403" ]; then
    print_pass
else
    print_fail "Esperado 403, obtenido $status"
fi

print_test "Command Injection bloqueado"
status=$(curl -k -s -o /dev/null -w "%{http_code}" "https://localhost/?cmd=ls|cat /etc/passwd" 2>/dev/null || echo "000")
if [ "$status" = "403" ]; then
    print_pass
else
    print_fail "Esperado 403, obtenido $status"
fi

print_test "Bot Scanner bloqueado"
status=$(curl -k -s -o /dev/null -w "%{http_code}" -A "sqlmap/1.0" https://localhost/ 2>/dev/null || echo "000")
if [ "$status" = "403" ]; then
    print_pass
else
    print_fail "Esperado 403, obtenido $status"
fi

# ================================
# FASE 5: Tests de GraphQL
# ================================
print_phase 5 "Tests de GraphQL"

print_test "GraphQL query básico funciona"
response=$(curl -k -s https://localhost/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{searchBooks(query:\"test\"){id}}"}"' 2>/dev/null || echo "")
if echo "$response" | grep -q "data"; then
    print_pass
else
    print_fail "GraphQL no responde correctamente"
fi

print_test "GraphQL introspection bloqueado"
status=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name}}}"}' 2>/dev/null || echo "000")
if [ "$status" = "403" ]; then
    print_pass
else
    print_fail "Esperado 403, obtenido $status"
fi

print_test "GraphQL con GET bloqueado"
status=$(curl -k -s -o /dev/null -w "%{http_code}" "https://localhost/graphql?query={books{title}}" 2>/dev/null || echo "000")
if [ "$status" = "405" ]; then
    print_pass
else
    print_fail "Esperado 405, obtenido $status"
fi

# ================================
# FASE 6: Tests de Rate Limiting
# ================================
print_phase 6 "Tests de Rate Limiting"

print_test "Rate limiting activo (general)"
blocked=0
for i in {1..20}; do
    status=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/ 2>/dev/null || echo "000")
    if [ "$status" = "429" ]; then
        blocked=$((blocked + 1))
    fi
done

if [ $blocked -gt 0 ]; then
    print_pass
    print_info "  $blocked peticiones bloqueadas por rate limit"
else
    print_fail "Rate limiting no se activó"
fi

# ================================
# FASE 7: Tests de Security Headers
# ================================
print_phase 7 "Tests de Security Headers"

headers=$(curl -k -s -I https://localhost/ 2>/dev/null || echo "")

print_test "Strict-Transport-Security presente"
if echo "$headers" | grep -qi "Strict-Transport-Security"; then
    print_pass
else
    print_fail "Header faltante"
fi

print_test "X-Frame-Options presente"
if echo "$headers" | grep -qi "X-Frame-Options"; then
    print_pass
else
    print_fail "Header faltante"
fi

print_test "X-Content-Type-Options presente"
if echo "$headers" | grep -qi "X-Content-Type-Options"; then
    print_pass
else
    print_fail "Header faltante"
fi

print_test "Content-Security-Policy presente"
if echo "$headers" | grep -qi "Content-Security-Policy"; then
    print_pass
else
    print_fail "Header faltante"
fi

# ================================
# FASE 8: Tests de Segmentación de Red
# ================================
print_phase 8 "Tests de Segmentación de Red"

print_test "Frontend NO puede acceder a PostgreSQL"
if docker exec bookworm_frontend ping -c 1 -W 1 bookworm_postgres &>/dev/null; then
    print_fail "Frontend puede acceder a DB (segmentación fallida)"
else
    print_pass
    print_info "  Segmentación correcta: acceso denegado"
fi

print_test "Gateway puede acceder a microservicios"
if docker exec graphql_gateway ping -c 1 -W 1 bookworm_users &>/dev/null; then
    print_pass
else
    print_fail "Gateway no puede acceder al backend"
fi

print_test "Bases de datos sin acceso a internet"
if docker exec bookworm_postgres ping -c 1 -W 1 8.8.8.8 &>/dev/null; then
    print_fail "DB tiene acceso a internet (segmentación fallida)"
else
    print_pass
    print_info "  Segmentación correcta: sin internet"
fi

# ================================
# FASE 9: Verificación de Logs
# ================================
print_phase 9 "Verificación de Logs"

print_test "Logs de Nginx generándose"
if [ -f "../../front/Frontend/logs/nginx/access.log" ] && [ -s "../../front/Frontend/logs/nginx/access.log" ]; then
    print_pass
    lines=$(wc -l < ../../front/Frontend/logs/nginx/access.log 2>/dev/null || echo "0")
    print_info "  $lines líneas en access.log"
else
    print_fail "Logs de Nginx vacíos o no existen"
fi

print_test "Logs de ModSecurity generándose"
if [ -f "../../front/Frontend/logs/modsec/audit.log" ]; then
    print_pass
    attacks=$(grep -c "ModSecurity:" ../../front/Frontend/logs/modsec/audit.log 2>/dev/null || echo "0")
    print_info "  $attacks eventos de seguridad registrados"
else
    print_fail "Logs de ModSecurity no existen"
fi

# ================================
# RESUMEN FINAL
# ================================
print_header "RESUMEN DE RESULTADOS"

echo ""
echo -e "${BLUE}Total de Tests:${NC}  $TESTS_TOTAL"
echo -e "${GREEN}Passed:${NC}         $TESTS_PASSED"
echo -e "${RED}Failed:${NC}         $TESTS_FAILED"
echo ""

# Calcular porcentaje
if [ $TESTS_TOTAL -gt 0 ]; then
    percentage=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    echo -e "${BLUE}Tasa de Éxito:${NC}  ${percentage}%"
fi

echo ""

# Resultado final
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║               ✅ TODOS LOS TESTS PASARON                   ║
║                                                            ║
║         🎉 SISTEMA COMPLETAMENTE FUNCIONAL 🎉              ║
║                                                            ║
║   ✓ WAF activo y protegiendo                              ║
║   ✓ Segmentación de red correcta                          ║
║   ✓ Microservicios operativos                             ║
║   ✓ GraphQL funcionando                                   ║
║   ✓ Logs generándose                                      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    exit 0
else
    echo -e "${RED}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║         ⚠️  ALGUNOS TESTS FALLARON                        ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo ""
    echo -e "${YELLOW}Recomendaciones:${NC}"
    echo "1. Verificar que todos los contenedores estén corriendo:"
    echo "   docker-compose -f docker-compose.full.yml ps"
    echo ""
    echo "2. Ver logs de errores:"
    echo "   docker-compose -f docker-compose.full.yml logs"
    echo ""
    echo "3. Reiniciar servicios si es necesario:"
    echo "   docker-compose -f docker-compose.full.yml restart"
    echo ""
    echo "4. Ver guía completa de troubleshooting:"
    echo "   cat TEST_COMPLETE_SYSTEM.md"
    echo ""

    exit 1
fi
