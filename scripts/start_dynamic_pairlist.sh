#!/bin/bash

# Script de démarrage du service de paires dynamiques
# Usage: ./start_dynamic_pairlist.sh [ADDRESS_TO_TRACK]

set -e

# Configuration par défaut
DEFAULT_ADDRESS="CHANGE_ME_TO_THE_ADDRESS_YOU_WANT_TO_TRACK"
TRACKED_ADDRESS="${1:-$DEFAULT_ADDRESS}"
REFRESH_PERIOD="${REFRESH_PERIOD:-900}"
MAX_PAIRS="${MAX_PAIRS:-50}"
MIN_PAIR_AGE_HOURS="${MIN_PAIR_AGE_HOURS:-1}"

echo "=================================================="
echo "DÉMARRAGE DU SERVICE DE PAIRES DYNAMIQUES"
echo "=================================================="
echo "Adresse suivie: $TRACKED_ADDRESS"
echo "Période de rafraîchissement: ${REFRESH_PERIOD}s"
echo "Maximum de paires: $MAX_PAIRS"
echo "Âge minimum des paires: ${MIN_PAIR_AGE_HOURS}h"
echo "=================================================="

# Vérifier si l'adresse a été configurée
if [ "$TRACKED_ADDRESS" = "$DEFAULT_ADDRESS" ]; then
    echo "⚠️  ATTENTION: Vous devez configurer l'adresse à suivre!"
    echo "Usage: $0 <ADRESSE_HYPERLIQUID>"
    echo "Exemple: $0 0x4b66f4048a0a90fd5ff44abbe5d68332656b78b8"
    echo ""
    echo "Ou définir la variable d'environnement:"
    echo "export TRACKED_ADDRESS=0x4b66f4048a0a90fd5ff44abbe5d68332656b78b8"
    echo ""
    read -p "Voulez-vous continuer avec l'adresse par défaut? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Créer le répertoire de données s'il n'existe pas
mkdir -p user_data/strategies/position_data
mkdir -p logs

# Fonction pour démarrer en mode standalone
start_standalone() {
    echo "🚀 Démarrage en mode standalone..."
    
    # Installer les dépendances si nécessaire
    if [ ! -f "venv/bin/activate" ]; then
        echo "📦 Création de l'environnement virtuel..."
        python3 -m venv venv
    fi
    
    echo "🔧 Activation de l'environnement virtuel..."
    source venv/bin/activate
    
    # Vérifier si les dépendances sont installées
    if ! python -c "import flask" 2>/dev/null; then
        echo "📦 Installation des dépendances..."
        pip install -r requirements-pairlist.txt
    fi
    
    echo "✅ Environnement prêt, démarrage du service..."
    
    # Démarrer le service
    python dynamic_pairlist_service.py \
        --address "$TRACKED_ADDRESS" \
        --refresh-period "$REFRESH_PERIOD" \
        --max-pairs "$MAX_PAIRS" \
        --port 5000 \
        --host 0.0.0.0
}

# Fonction pour démarrer avec Docker
start_docker() {
    echo "🐳 Démarrage avec Docker..."
    
    # Créer le réseau s'il n'existe pas
    docker network create freqtrade-network 2>/dev/null || true
    
    # Exporter les variables d'environnement
    export TRACKED_ADDRESS
    export REFRESH_PERIOD
    export MAX_PAIRS
    export MIN_PAIR_AGE_HOURS
    
    # Construire et démarrer le service
    docker-compose -f docker-compose-pairlist.yml up --build -d
    
    echo "✅ Service démarré en arrière-plan"
    echo "📊 Logs: docker-compose -f docker-compose-pairlist.yml logs -f"
    echo "🔍 Test: python test_dynamic_pairlist.py"
    echo "🛑 Arrêt: docker-compose -f docker-compose-pairlist.yml down"
}

# Fonction pour tester le service
test_service() {
    echo "🧪 Test du service..."
    sleep 5  # Attendre que le service démarre
    
    if command -v python3 &> /dev/null; then
        python3 test_dynamic_pairlist.py
    else
        echo "❌ Python3 non trouvé pour les tests"
    fi
}

# Menu de sélection du mode
echo ""
echo "Choisissez le mode de démarrage:"
echo "1) Standalone (Python local)"
echo "2) Docker (recommandé)"
echo "3) Test uniquement"
echo ""
read -p "Votre choix (1-3): " -n 1 -r
echo ""

case $REPLY in
    1)
        start_standalone
        ;;
    2)
        start_docker
        echo ""
        echo "⏳ Attente du démarrage du service..."
        sleep 10
        test_service
        ;;
    3)
        test_service
        ;;
    *)
        echo "❌ Choix invalide"
        exit 1
        ;;
esac

echo ""
echo "✅ Script terminé!"