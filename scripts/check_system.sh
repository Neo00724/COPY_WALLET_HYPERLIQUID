#!/bin/bash

# Script de vérification complète du système
# Vérifie que tout fonctionne après l'organisation du projet

echo "🔍 Vérification complète du système de copy trading"
echo "=" * 60

# 1. Vérifier la structure du projet
echo "📁 Vérification de la structure du projet..."

required_files=(
    "docker-compose.yml"
    "Dockerfile.technical"
    "Dockerfile.pairlist"
    "dynamic_pairlist_service.py"
    ".env"
    "user_data/config.json"
    "user_data/strategies/COPY_HL.py"
)

required_scripts=(
    "scripts/sync_positions.sh"
    "scripts/validate_config.py"
    "scripts/start_dynamic_pairlist.sh"
    "scripts/show_PnL.py"
    "scripts/track_account.py"
    "scripts/fetch_current_positions.py"
)

missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

for script in "${required_scripts[@]}"; do
    if [ ! -f "$script" ]; then
        missing_files+=("$script")
    fi
done

if [ ${#missing_files[@]} -eq 0 ]; then
    echo "✅ Tous les fichiers requis sont présents"
else
    echo "❌ Fichiers manquants:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    exit 1
fi

# 2. Vérifier la configuration
echo ""
echo "⚙️ Validation de la configuration..."
if python3 scripts/validate_config.py; then
    echo "✅ Configuration valide"
else
    echo "❌ Problème de configuration"
    exit 1
fi

# 3. Vérifier Docker
echo ""
echo "🐳 Vérification de Docker..."
if docker --version > /dev/null 2>&1; then
    echo "✅ Docker disponible"
else
    echo "❌ Docker non disponible"
    exit 1
fi

if docker-compose --version > /dev/null 2>&1; then
    echo "✅ Docker Compose disponible"
else
    echo "❌ Docker Compose non disponible"
    exit 1
fi

# 4. Vérifier les services (s'ils sont en cours d'exécution)
echo ""
echo "🔍 Vérification des services..."

if docker-compose ps | grep -q "dynamic-pairlist.*Up"; then
    echo "✅ Service de paires en cours d'exécution"
    
    # Tester l'API
    if curl -s http://localhost:5001/health > /dev/null; then
        echo "✅ API du service de paires accessible"
        
        # Vérifier le nombre de paires
        pairs_count=$(curl -s http://localhost:5001/pairlist | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('pairs', [])))" 2>/dev/null)
        if [ "$pairs_count" -gt 5 ]; then
            echo "✅ Service génère $pairs_count paires (> 5 paires de base)"
        else
            echo "⚠️  Service génère seulement $pairs_count paires"
            echo "💡 Exécutez: ./scripts/sync_positions.sh"
        fi
    else
        echo "❌ API du service de paires non accessible"
    fi
else
    echo "ℹ️  Service de paires non en cours d'exécution"
    echo "💡 Démarrez avec: docker-compose up -d"
fi

if docker-compose ps | grep -q "freqtrade.*Up"; then
    echo "✅ FreqTrade en cours d'exécution"
else
    echo "ℹ️  FreqTrade non en cours d'exécution"
fi

# 5. Vérifier les permissions des scripts
echo ""
echo "🔐 Vérification des permissions..."
for script in scripts/*.sh scripts/*.py; do
    if [ -x "$script" ]; then
        echo "✅ $script exécutable"
    else
        echo "⚠️  $script non exécutable"
        chmod +x "$script"
        echo "   → Permission ajoutée"
    fi
done

echo ""
echo "=" * 60
echo "🎉 Vérification terminée !"
echo ""
echo "📋 Commandes utiles:"
echo "   - Démarrer: docker-compose up --build -d"
echo "   - Synchroniser: ./scripts/sync_positions.sh"
echo "   - Valider: ./scripts/validate_config.py"
echo "   - Logs: docker-compose logs -f"
echo "   - Arrêter: docker-compose down"
echo ""
echo "🌐 Endpoints:"
echo "   - Service de paires: http://localhost:5001/pairlist"
echo "   - FreqTrade API: http://localhost:3000/api/v1/status"