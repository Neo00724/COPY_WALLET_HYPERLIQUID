#!/usr/bin/env python3
"""
Service de génération dynamique de paires basé sur les positions du compte copié.
Ce service analyse l'historique des positions et génère une liste de paires
qui inclut toutes les paires qui ont été tradées par le compte copié.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import logging
from flask import Flask, jsonify, request
import threading
import schedule

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PairInfo:
    """Information sur une paire tradée"""
    coin: str
    pair: str  # Format FreqTrade (ex: BTC/USDC:USDC)
    first_seen: datetime
    last_seen: datetime
    total_trades: int
    is_active: bool  # Position actuellement ouverte

class DynamicPairListService:
    """Service de génération dynamique de paires"""
    
    def __init__(self, 
                 tracked_address: str,
                 position_data_dir: str = "user_data/strategies/position_data",
                 refresh_period: int = 900,  # 15 minutes par défaut
                 min_pair_age_hours: int = 1,  # Minimum 1h avant d'ajouter une paire
                 max_pairs: int = 50):
        
        self.tracked_address = tracked_address
        self.position_data_dir = Path(position_data_dir)
        self.refresh_period = refresh_period
        self.min_pair_age_hours = min_pair_age_hours
        self.max_pairs = max_pairs
        
        # Données en mémoire
        self.tracked_pairs: Dict[str, PairInfo] = {}
        self.current_pairlist: List[str] = []
        self.last_update: Optional[datetime] = None
        
        # Paires de base toujours incluses
        self.base_pairs = [
            "BTC/USDC:USDC", "ETH/USDC:USDC", "SOL/USDC:USDC", 
            "BNB/USDC:USDC", "XRP/USDC:USDC"
        ]
        
        # Initialisation
        self._load_historical_data()
        self._update_pairlist()
        
    def _load_historical_data(self) -> None:
        """Charge l'historique des positions depuis les fichiers CSV"""
        try:
            changes_file = self.position_data_dir / "changes_log.csv"
            positions_file = self.position_data_dir / "positions_history.csv"
            
            if not changes_file.exists():
                logger.info("Aucun fichier d'historique trouvé, démarrage avec les paires de base")
                return
                
            import csv
            
            # Charger l'historique des changements
            with open(changes_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    coin = row['coin']
                    timestamp = int(row['timestamp'])
                    change_time = datetime.fromtimestamp(timestamp / 1000)
                    
                    pair = f"{coin}/USDC:USDC"
                    
                    if coin not in self.tracked_pairs:
                        self.tracked_pairs[coin] = PairInfo(
                            coin=coin,
                            pair=pair,
                            first_seen=change_time,
                            last_seen=change_time,
                            total_trades=1,
                            is_active=False
                        )
                    else:
                        self.tracked_pairs[coin].last_seen = max(
                            self.tracked_pairs[coin].last_seen, change_time
                        )
                        self.tracked_pairs[coin].total_trades += 1
                        
            # Vérifier les positions actuellement ouvertes
            last_positions_file = self.position_data_dir / "last_positions.csv"
            if last_positions_file.exists():
                with open(last_positions_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    active_coins = set()
                    for row in reader:
                        coin = row['coin']
                        active_coins.add(coin)
                        if coin in self.tracked_pairs:
                            self.tracked_pairs[coin].is_active = True
                            
            logger.info(f"Chargé {len(self.tracked_pairs)} paires depuis l'historique")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'historique: {e}")
    
    def _get_current_positions(self) -> Set[str]:
        """Récupère les positions actuellement ouvertes avec stratégie de fallback"""
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            perp_data = info.user_state(self.tracked_address)
            
            current_coins = set()
            for asset_pos in perp_data.get('assetPositions', []):
                if asset_pos['type'] == 'oneWay' and 'position' in asset_pos:
                    pos = asset_pos['position']
                    size = float(pos['szi'])
                    if size != 0:  # Position active
                        current_coins.add(pos['coin'])
            
            logger.info(f"API Hyperliquid: {len(current_coins)} positions actives récupérées")
            return current_coins
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des positions: {e}")
            
            # Stratégie de fallback : utiliser les dernières positions connues
            fallback_coins = self._get_fallback_positions()
            if fallback_coins:
                logger.info(f"Fallback: {len(fallback_coins)} positions depuis les données locales")
                return fallback_coins
            
            # Dernier recours : paires populaires par défaut
            default_coins = self._get_default_popular_pairs()
            logger.info(f"Défaut: {len(default_coins)} paires populaires utilisées")
            return default_coins
    
    def _get_fallback_positions(self) -> Set[str]:
        """Récupère les dernières positions connues depuis les fichiers CSV"""
        try:
            last_positions_file = self.position_data_dir / "last_positions.csv"
            if not last_positions_file.exists():
                return set()
            
            import csv
            active_coins = set()
            with open(last_positions_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    coin = row['coin']
                    active_coins.add(coin)
            
            return active_coins
            
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des positions de fallback: {e}")
            return set()
    
    def _get_default_popular_pairs(self) -> Set[str]:
        """Retourne un ensemble de paires populaires par défaut"""
        # Paires populaires couramment tradées sur Hyperliquid
        popular_pairs = {
            'BTC', 'ETH', 'SOL', 'AVAX', 'DOGE', 'XRP', 'ADA', 'LINK',
            'AAVE', 'LDO', 'TRX', 'PENGU', 'TRUMP', 'FARTCOIN', 'kPEPE',
            'NEIROETH', 'BIO', 'WLFI', 'kFLOKI'
        }
        return popular_pairs
    
    def _update_tracked_pairs(self) -> None:
        """Met à jour la liste des paires suivies"""
        current_coins = self._get_current_positions()
        now = datetime.now()
        
        # Marquer les paires actives/inactives
        for coin, pair_info in self.tracked_pairs.items():
            pair_info.is_active = coin in current_coins
            if coin in current_coins:
                pair_info.last_seen = now
        
        # Ajouter les nouvelles paires détectées
        for coin in current_coins:
            if coin not in self.tracked_pairs:
                pair = f"{coin}/USDC:USDC"
                self.tracked_pairs[coin] = PairInfo(
                    coin=coin,
                    pair=pair,
                    first_seen=now,
                    last_seen=now,
                    total_trades=1,
                    is_active=True
                )
                logger.info(f"Nouvelle paire détectée: {pair}")
    
    def _filter_pairs_by_criteria(self) -> List[str]:
        """Filtre les paires selon les critères définis"""
        now = datetime.now()
        min_age = timedelta(hours=self.min_pair_age_hours)
        
        eligible_pairs = []
        
        # Toujours inclure les paires de base
        eligible_pairs.extend(self.base_pairs)
        
        # Ajouter les paires qui respectent les critères
        for coin, pair_info in self.tracked_pairs.items():
            # Ignorer si déjà dans les paires de base
            if pair_info.pair in self.base_pairs:
                continue
                
            # Critères d'inclusion:
            # 1. Paire assez ancienne OU actuellement active
            # 2. A été tradée récemment (dans les 30 derniers jours)
            age = now - pair_info.first_seen
            time_since_last_trade = now - pair_info.last_seen
            
            if (age >= min_age or pair_info.is_active) and time_since_last_trade <= timedelta(days=30):
                eligible_pairs.append(pair_info.pair)
        
        # Limiter le nombre total de paires
        if len(eligible_pairs) > self.max_pairs:
            # Prioriser: paires actives > récemment tradées > plus tradées
            def sort_key(pair):
                coin = pair.split('/')[0]
                if coin not in self.tracked_pairs:
                    return (1, 0, 0)  # Paires de base
                
                pair_info = self.tracked_pairs[coin]
                return (
                    0 if pair_info.is_active else 1,  # Actives en premier
                    -pair_info.last_seen.timestamp(),  # Plus récentes en premier
                    -pair_info.total_trades  # Plus tradées en premier
                )
            
            eligible_pairs.sort(key=sort_key)
            eligible_pairs = eligible_pairs[:self.max_pairs]
        
        return list(set(eligible_pairs))  # Supprimer les doublons
    
    def _update_pairlist(self) -> None:
        """Met à jour la liste de paires"""
        try:
            self._update_tracked_pairs()
            new_pairlist = self._filter_pairs_by_criteria()
            
            if new_pairlist != self.current_pairlist:
                old_count = len(self.current_pairlist)
                self.current_pairlist = new_pairlist
                self.last_update = datetime.now()
                
                logger.info(f"Liste de paires mise à jour: {old_count} -> {len(new_pairlist)} paires")
                logger.info(f"Nouvelles paires: {new_pairlist}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la liste: {e}")
    
    def get_pairlist_response(self) -> Dict[str, Any]:
        """Retourne la réponse au format RemotePairList"""
        return {
            "pairs": self.current_pairlist,
            "refresh_period": self.refresh_period,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "total_tracked_pairs": len(self.tracked_pairs),
            "active_pairs": len([p for p in self.tracked_pairs.values() if p.is_active])
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques détaillées"""
        now = datetime.now()
        return {
            "service_info": {
                "tracked_address": self.tracked_address,
                "refresh_period": self.refresh_period,
                "min_pair_age_hours": self.min_pair_age_hours,
                "max_pairs": self.max_pairs,
                "last_update": self.last_update.isoformat() if self.last_update else None
            },
            "current_pairlist": {
                "total_pairs": len(self.current_pairlist),
                "pairs": self.current_pairlist
            },
            "tracked_pairs": {
                "total": len(self.tracked_pairs),
                "active": len([p for p in self.tracked_pairs.values() if p.is_active]),
                "details": [
                    {
                        "coin": pair_info.coin,
                        "pair": pair_info.pair,
                        "first_seen": pair_info.first_seen.isoformat(),
                        "last_seen": pair_info.last_seen.isoformat(),
                        "total_trades": pair_info.total_trades,
                        "is_active": pair_info.is_active,
                        "age_hours": (now - pair_info.first_seen).total_seconds() / 3600
                    }
                    for pair_info in sorted(self.tracked_pairs.values(), 
                                          key=lambda x: x.last_seen, reverse=True)
                ]
            }
        }
    
    def start_scheduler(self) -> None:
        """Démarre le planificateur de mise à jour"""
        schedule.every(self.refresh_period).seconds.do(self._update_pairlist)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Vérifier toutes les minutes
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info(f"Planificateur démarré (mise à jour toutes les {self.refresh_period}s)")

# Configuration Flask
app = Flask(__name__)

# Instance globale du service
service = None

def init_service(tracked_address: str = None, **kwargs):
    """Initialise le service avec l'adresse à suivre"""
    global service
    
    if tracked_address is None:
        # Essayer de lire depuis la stratégie
        try:
            from user_data.strategies.COPY_HL import ADDRESS_TO_TRACK_TOP
            tracked_address = ADDRESS_TO_TRACK_TOP
        except:
            tracked_address = "CHANGE_ME_TO_THE_ADDRESS_YOU_WANT_TO_TRACK"
    
    service = DynamicPairListService(tracked_address, **kwargs)
    service.start_scheduler()
    return service

@app.route('/pairlist')
def get_pairlist():
    """Endpoint principal pour FreqTrade RemotePairList"""
    if service is None:
        return jsonify({"error": "Service non initialisé"}), 500
    
    return jsonify(service.get_pairlist_response())

@app.route('/stats')
def get_stats():
    """Endpoint pour les statistiques détaillées"""
    if service is None:
        return jsonify({"error": "Service non initialisé"}), 500
    
    return jsonify(service.get_stats())

@app.route('/health')
def health_check():
    """Endpoint de santé"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service_initialized": service is not None
    })

@app.route('/refresh', methods=['POST'])
def force_refresh():
    """Force une mise à jour de la liste"""
    if service is None:
        return jsonify({"error": "Service non initialisé"}), 500
    
    service._update_pairlist()
    return jsonify({
        "message": "Mise à jour forcée effectuée",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Service de génération dynamique de paires")
    parser.add_argument("--address", help="Adresse du compte à suivre")
    parser.add_argument("--port", type=int, default=5000, help="Port du serveur")
    parser.add_argument("--host", default="0.0.0.0", help="Host du serveur")
    parser.add_argument("--refresh-period", type=int, default=900, help="Période de rafraîchissement en secondes")
    parser.add_argument("--max-pairs", type=int, default=50, help="Nombre maximum de paires")
    
    args = parser.parse_args()
    
    # Initialiser le service
    init_service(
        tracked_address=args.address,
        refresh_period=args.refresh_period,
        max_pairs=args.max_pairs
    )
    
    logger.info(f"Démarrage du service sur {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)