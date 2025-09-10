#!/usr/bin/env python3
"""
Script de validation de la configuration du service de paires dynamiques.
Vérifie que toutes les variables d'environnement sont correctement configurées.
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Charge le fichier .env et retourne les variables"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Fichier .env non trouvé")
        return {}
    
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    return env_vars

def validate_configuration():
    """Valide la configuration complète"""
    print("🔍 Validation de la configuration du service de paires dynamiques")
    print("=" * 70)
    
    # Charger les variables d'environnement
    env_vars = load_env_file()
    
    # Variables requises
    required_vars = {
        'TRACKED_ADDRESS': 'Adresse Hyperliquid à suivre',
        'REFRESH_PERIOD': 'Période de rafraîchissement (secondes)',
        'MAX_PAIRS': 'Nombre maximum de paires',
        'MIN_PAIR_AGE_HOURS': 'Âge minimum des paires (heures)'
    }
    
    print("📋 Variables d'environnement:")
    all_good = True
    
    for var, description in required_vars.items():
        if var in env_vars:
            value = env_vars[var]
            if var == 'TRACKED_ADDRESS':
                if value == 'CHANGE_ME_TO_THE_ADDRESS_YOU_WANT_TO_TRACK':
                    print(f"  ⚠️  {var}: {value} (DOIT ÊTRE CONFIGURÉ)")
                    all_good = False
                elif value.startswith('0x') and len(value) == 42:
                    print(f"  ✅ {var}: {value}")
                else:
                    print(f"  ❌ {var}: {value} (FORMAT INVALIDE)")
                    all_good = False
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: NON DÉFINI ({description})")
            all_good = False
    
    print("\n📁 Fichiers requis:")
    
    # Vérifier les fichiers requis
    required_files = {
        'docker-compose.yml': 'Configuration Docker',
        'Dockerfile.pairlist': 'Image Docker du service',
        'dynamic_pairlist_service.py': 'Service principal',
        'user_data/config.json': 'Configuration FreqTrade',
        'user_data/strategies/COPY_HL.py': 'Stratégie de copy trading'
    }
    
    for file_path, description in required_files.items():
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}: MANQUANT ({description})")
            all_good = False
    
    print("\n🔧 Configuration FreqTrade:")
    
    # Vérifier la configuration FreqTrade
    config_file = Path("user_data/config.json")
    if config_file.exists():
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Vérifier la configuration des pairlists
            pairlists = config.get('pairlists', [])
            if pairlists and len(pairlists) > 0:
                pairlist_config = pairlists[0]
                if pairlist_config.get('method') == 'RemotePairList':
                    url = pairlist_config.get('pairlist_url', '')
                    if 'dynamic-pairlist-service:5000' in url:
                        print(f"  ✅ RemotePairList configuré: {url}")
                    else:
                        print(f"  ⚠️  URL incorrecte: {url}")
                        print("      Devrait être: http://dynamic-pairlist-service:5000/pairlist")
                else:
                    print(f"  ❌ Méthode incorrecte: {pairlist_config.get('method')}")
                    all_good = False
            else:
                print("  ❌ Aucune pairlist configurée")
                all_good = False
                
        except Exception as e:
            print(f"  ❌ Erreur lecture config.json: {e}")
            all_good = False
    
    print("\n🐳 Configuration Docker:")
    
    # Vérifier docker-compose.yml
    docker_compose = Path("docker-compose.yml")
    if docker_compose.exists():
        with open(docker_compose, 'r') as f:
            content = f.read()
            if 'dynamic-pairlist' in content and 'freqtrade' in content:
                print("  ✅ Services dynamic-pairlist et freqtrade configurés")
            else:
                print("  ❌ Services manquants dans docker-compose.yml")
                all_good = False
            
            if 'depends_on' in content and 'service_healthy' in content:
                print("  ✅ Dépendances et health checks configurés")
            else:
                print("  ⚠️  Health checks ou dépendances manquants")
    
    print("\n" + "=" * 70)
    
    if all_good:
        print("🎉 CONFIGURATION VALIDE !")
        print("✅ Vous pouvez démarrer avec: docker-compose up --build -d")
        return True
    else:
        print("❌ CONFIGURATION INCOMPLÈTE")
        print("🔧 Corrigez les erreurs ci-dessus avant de démarrer")
        return False

def main():
    """Fonction principale"""
    try:
        success = validate_configuration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erreur lors de la validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()