# 🚀 Copy Trading Bot - FreqTrade + Hyperliquid

Bot de copy trading automatisé avec service de paires dynamiques pour Hyperliquid.

## ⚡ Démarrage Rapide

```bash
# 1. Configurer l'adresse dans .env
nano .env  # Modifier TRACKED_ADDRESS

# 2. Démarrer avec Docker
docker-compose up --build -d

# 3. Synchroniser les positions (première fois)
./scripts/sync_positions.sh

# 4. Vérifier le fonctionnement
curl http://localhost:5001/pairlist
```

## 🎯 Fonctionnalités

- ✅ **Paires dynamiques** : Détection automatique des nouvelles paires (29 paires au lieu de 5 fixes)
- ✅ **Copy trading** : Réplication des positions d'un compte Hyperliquid
- ✅ **Docker unifié** : Démarrage en une commande
- ✅ **Configuration centralisée** : Variables d'environnement dans .env
- ✅ **Stratégie de fallback** : Fonctionne même sans accès API direct

## 🏗️ Architecture

```
Services Docker:
├── dynamic-pairlist:5001  # Service de paires dynamiques
└── freqtrade:3000         # Bot de trading FreqTrade
```

## 📊 Résultats

Le service détecte automatiquement **29 paires** basées sur le compte copié :
- **Cryptos majeurs** : BTC, ETH, SOL, AVAX, DOGE, XRP, ADA, LINK
- **DeFi tokens** : AAVE, EIGEN, ENA, SUI, TAO, WLD
- **Memecoins** : TRUMP, FARTCOIN, kPEPE, kFLOKI, NEIROETH, MOODENG
- **Nouveaux tokens** : AI16Z, SYRUP, VVV, YZY, LAUNCHCOIN, PUMP

## 📁 Structure du Projet

```
├── docker-compose.yml              # Configuration Docker unifiée
├── .env                            # Variables d'environnement centralisées
├── Dockerfile.technical            # Image FreqTrade
├── Dockerfile.pairlist             # Image service de paires
├── dynamic_pairlist_service.py     # Service principal
├── scripts/                        # Scripts utilitaires
│   ├── sync_positions.sh           # Synchronisation des positions
│   ├── validate_config.py          # Validation de la configuration
│   ├── fetch_current_positions.py  # Récupération manuelle des positions
│   ├── start_dynamic_pairlist.sh   # Démarrage standalone
│   ├── show_PnL.py                 # Affichage des P&L
│   └── track_account.py            # Suivi de compte
├── docs/                           # Documentation
└── user_data/                      # Configuration FreqTrade
    ├── config.json                 # Configuration principale
    └── strategies/
        └── COPY_HL.py              # Stratégie de copy trading
```

## 🔧 Configuration (.env)

```bash
# === CONFIGURATION FREQTRADE ===
FREQTRADE__EXCHANGE__NAME=hyperliquid
FREQTRADE__EXCHANGE__KEY=Your_Exchange_Key
FREQTRADE__EXCHANGE__SECRET=Your_Exchange_Secret

# === SERVICE DE PAIRES DYNAMIQUES ===
TRACKED_ADDRESS=0xe61c2251b2641989f49bb5b73b2a8d0dbc6e40d8
REFRESH_PERIOD=900
MAX_PAIRS=50
MIN_PAIR_AGE_HOURS=1
```

## 🛠️ Scripts Utilitaires

### Gestion du Système
```bash
# Validation de la configuration
./scripts/validate_config.py

# Synchronisation des positions
./scripts/sync_positions.sh

# Démarrage standalone du service
./scripts/start_dynamic_pairlist.sh
```

### Monitoring
```bash
# Affichage des P&L
./scripts/show_PnL.py

# Suivi de compte
./scripts/track_account.py
```

## 🌐 Endpoints

### Service de Paires (Port 5001)
- **`/pairlist`** - Liste pour FreqTrade (format RemotePairList)
- **`/stats`** - Statistiques détaillées
- **`/health`** - État du service
- **`/refresh`** - Forcer une mise à jour

### FreqTrade API (Port 3000)
- **`/api/v1/status`** - Statut du bot
- **`/api/v1/trades`** - Trades en cours

## 🔄 Workflow

### Démarrage Initial
1. **Configuration** : Modifier `TRACKED_ADDRESS` dans `.env`
2. **Démarrage** : `docker-compose up --build -d`
3. **Synchronisation** : `./scripts/sync_positions.sh`
4. **Vérification** : `curl http://localhost:5001/pairlist`

### Utilisation Quotidienne
- **Automatique** : Le système fonctionne de manière autonome
- **Mise à jour** : Paires rafraîchies toutes les 15 minutes
- **Monitoring** : `docker-compose logs -f`

## 🚨 Points Importants

1. **Première synchronisation** : Exécutez `./scripts/sync_positions.sh` après le premier démarrage
2. **Configuration centralisée** : Toutes les variables dans `.env`
3. **Dockerfiles séparés** : Architecture microservices optimale
4. **Scripts organisés** : Tous dans le dossier `scripts/`

## 🎉 Transformation

**Avant** : 5 paires fixes → nouvelles paires ignorées  
**Après** : 29 paires dynamiques → adaptation automatique complète

---

**Développé pour automatiser le copy trading sur Hyperliquid** 🎯
