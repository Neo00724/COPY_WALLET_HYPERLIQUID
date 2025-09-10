# 📁 Scripts Utilitaires - Service de Paires Dynamiques

Ce dossier contient tous les scripts utilitaires pour le système de copy trading.

## 🔧 Scripts de Gestion

### [`sync_positions.sh`](sync_positions.sh)
**Synchronisation automatique des positions**
```bash
./scripts/sync_positions.sh
```
- Récupère les positions actuelles du compte copié
- Sauvegarde les données dans position_data/
- Redémarre les services pour appliquer les changements
- **À exécuter** après suppression des données ou premier démarrage

### [`validate_config.py`](validate_config.py)
**Validation de la configuration**
```bash
./scripts/validate_config.py
```
- Vérifie que toutes les variables d'environnement sont configurées
- Contrôle l'existence des fichiers requis
- Valide la configuration FreqTrade et Docker
- **À exécuter** avant le démarrage pour éviter les erreurs

### [`start_dynamic_pairlist.sh`](start_dynamic_pairlist.sh)
**Démarrage standalone du service**
```bash
./scripts/start_dynamic_pairlist.sh 0xADRESSE
```
- Démarre le service de paires en mode Python local
- Alternative au démarrage Docker
- Utile pour le développement et debugging

## 📊 Scripts de Monitoring

### [`show_PnL.py`](show_PnL.py)
**Affichage des profits et pertes**
```bash
./scripts/show_PnL.py
```
- Affiche les P&L des positions ouvertes
- Analyse des performances du copy trading
- Comparaison avec le compte copié

### [`track_account.py`](track_account.py)
**Suivi détaillé du compte**
```bash
./scripts/track_account.py
```
- Suivi en temps réel des changements de position
- Historique des trades du compte copié
- Génération de rapports détaillés

### [`fetch_current_positions.py`](fetch_current_positions.py)
**Récupération manuelle des positions**
```bash
./scripts/fetch_current_positions.py --from-env
```
- Récupère les positions actuelles depuis l'API Hyperliquid
- Sauvegarde dans les fichiers CSV
- Utile pour debugging ou récupération manuelle

## 🎯 Utilisation Typique

### Démarrage Complet
```bash
# 1. Valider la configuration
./scripts/validate_config.py

# 2. Démarrer les services
docker-compose up --build -d

# 3. Synchroniser les positions
./scripts/sync_positions.sh

# 4. Vérifier le fonctionnement
curl http://localhost:5001/pairlist
```

### Monitoring Quotidien
```bash
# Voir les P&L
./scripts/show_PnL.py

# Suivre les changements
./scripts/track_account.py

# Vérifier la configuration
./scripts/validate_config.py
```

### Dépannage
```bash
# Récupérer manuellement les positions
./scripts/fetch_current_positions.py --from-env

# Resynchroniser tout
./scripts/sync_positions.sh

# Démarrer en mode standalone pour debugging
./scripts/start_dynamic_pairlist.sh 0xADRESSE
```

## 📋 Permissions

Tous les scripts sont exécutables :
```bash
chmod +x scripts/*.sh scripts/*.py
```

## 🔗 Dépendances

- **Docker** : Pour les scripts utilisant docker-compose
- **Python 3** : Pour tous les scripts Python
- **curl** : Pour les tests d'API
- **SDK Hyperliquid** : Pour la récupération des positions (installé dans les containers)

---

**Scripts organisés pour une gestion optimale du système de copy trading** 🚀