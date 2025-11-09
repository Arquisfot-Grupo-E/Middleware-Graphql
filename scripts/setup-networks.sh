#!/bin/bash

# =============================================================================
# Script de Configuración de Redes para BookWorm
# =============================================================================
# Este script crea las 3 redes segmentadas que usará toda la plataforma.
# Solo necesitas ejecutarlo UNA VEZ antes de levantar los servicios.
#
# Uso:
#   bash scripts/setup-networks.sh
#
# Redes que se crean:
#   1. dmz_network (172.20.0.0/24) - Zona pública
#   2. backend_network (172.21.0.0/24) - Microservicios
#   3. data_network (172.22.0.0/24) - Bases de datos (sin internet)
# =============================================================================

echo "🌐 Configurando Redes de BookWorm..."
echo ""

# -----------------------------------------------------------------------------
# RED 1: DMZ Network (Zona Pública)
# -----------------------------------------------------------------------------
echo "🟢 Creando dmz_network (172.20.0.0/24)..."
echo "   → Servicios: Frontend, GraphQL Gateway (interfaz pública)"

docker network create \
  --driver bridge \
  --subnet 172.20.0.0/24 \
  --gateway 172.20.0.1 \
  dmz_network 2>/dev/null && echo "   ✅ dmz_network creada" || echo "   ℹ️  dmz_network ya existe"

echo ""

# -----------------------------------------------------------------------------
# RED 2: Backend Network (Capa de Aplicación)
# -----------------------------------------------------------------------------
echo "🟡 Creando backend_network (172.21.0.0/24)..."
echo "   → Servicios: GraphQL Gateway, Back-users, Back-reviews, Back-recommendations, Back-scraping"

docker network create \
  --driver bridge \
  --subnet 172.21.0.0/24 \
  --gateway 172.21.0.1 \
  backend_network 2>/dev/null && echo "   ✅ backend_network creada" || echo "   ℹ️  backend_network ya existe"

echo ""

# -----------------------------------------------------------------------------
# RED 3: Data Network (Capa de Datos - SIN Internet)
# -----------------------------------------------------------------------------
echo "🔴 Creando data_network (172.22.0.0/24)..."
echo "   → Servicios: PostgreSQL, MongoDB, Neo4j, MySQL, Kafka"
echo "   → internal=true (SIN acceso a internet)"

docker network create \
  --driver bridge \
  --subnet 172.22.0.0/24 \
  --gateway 172.22.0.1 \
  --internal \
  data_network 2>/dev/null && echo "   ✅ data_network creada" || echo "   ℹ️  data_network ya existe"

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "✅ Configuración de Redes Completada"
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Redes disponibles:"
docker network ls | grep -E "NETWORK ID|dmz_network|backend_network|data_network"
echo ""
echo "🔍 Para inspeccionar una red:"
echo "   docker network inspect dmz_network"
echo "   docker network inspect backend_network"
echo "   docker network inspect data_network"
echo ""
echo "🚀 Ahora puedes levantar los servicios con:"
echo "   docker-compose -f docker-compose.full.yml up --build"
echo ""
