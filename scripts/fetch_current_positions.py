#!/usr/bin/env python3
"""
Script pour récupérer les positions actuelles du compte copié
et les sauvegarder pour le service de paires dynamiques.
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path

def fetch_positions(address):
    """Récupère les positions actuelles depuis l'API Hyperliquid"""
    try:
        # Essayer d'importer le SDK
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
        except ImportError:
            print("❌ SDK Hyperliquid non installé")
            print("💡 Installez avec: pip install hyperliquid-python-sdk==0.18.0")
            return None
        
        print(f"🔍 Récupération des positions pour {address}...")
        
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        perp_data = info.user_state(address)
        
        if not perp_data:
            print("❌ Aucune donnée récupérée")
            return None
        
        # Extraire les positions
        positions = []
        timestamp = perp_data.get('time', int(datetime.now().timestamp() * 1000))
        
        for asset_pos in perp_data.get('assetPositions', []):
            if asset_pos['type'] == 'oneWay' and 'position' in asset_pos:
                pos = asset_pos['position']
                coin = pos['coin']
                size = float(pos['szi'])
                
                # Ignorer les positions fermées
                if size == 0:
                    continue
                
                leverage_value = pos['leverage']['value'] if isinstance(pos['leverage'], dict) else pos['leverage']
                
                position_data = {
                    'coin': coin,
                    'size': size,
                    'entry_price': float(pos['entryPx']),
                    'position_value': float(pos['positionValue']),
                    'unrealized_pnl': float(pos['unrealizedPnl']),
                    'leverage': float(leverage_value),
                    'margin_used': float(pos['marginUsed']),
                    'timestamp': timestamp,
                    'human_time': datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                }
                positions.append(position_data)
        
        print(f"✅ {len(positions)} positions actives récupérées")
        return positions
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération: {e}")
        return None

def save_positions(positions, data_dir="user_data/strategies/position_data"):
    """Sauvegarde les positions dans les fichiers CSV"""
    try:
        # Créer le répertoire
        os.makedirs(data_dir, exist_ok=True)
        
        # Fichier des dernières positions
        last_positions_file = os.path.join(data_dir, "last_positions.csv")
        
        print(f"💾 Sauvegarde dans {last_positions_file}...")
        
        with open(last_positions_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'coin', 'size', 'entry_price', 'position_value', 
                'unrealized_pnl', 'leverage', 'margin_used', 'timestamp', 'human_time'
            ])
            
            for pos in positions:
                writer.writerow([
                    pos['coin'], pos['size'], pos['entry_price'], pos['position_value'],
                    pos['unrealized_pnl'], pos['leverage'], pos['margin_used'], 
                    pos['timestamp'], pos['human_time']
                ])
        
        # Fichier des changements (pour initialiser)
        changes_file = os.path.join(data_dir, "changes_log.csv")
        
        with open(changes_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'coin', 'change_type', 'old_size', 'new_size', 
                'old_position_value', 'new_position_value', 'timestamp', 'human_time'
            ])
            
            # Ajouter toutes les positions comme "ouvertes"
            for pos in positions:
                position_type = "long" if pos['size'] > 0 else "short"
                writer.writerow([
                    pos['coin'], f'opened_{position_type}', '', pos['size'],
                    '', pos['position_value'], pos['timestamp'], pos['human_time']
                ])
        
        print(f"✅ {len(positions)} positions sauvegardées")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        return False

def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Récupérer les positions actuelles du compte copié")
    parser.add_argument("--address", help="Adresse Hyperliquid à analyser")
    parser.add_argument("--from-env", action="store_true", help="Utiliser TRACKED_ADDRESS depuis .env")
    
    args = parser.parse_args()
    
    # Récupérer l'adresse
    if args.from_env:
        # Charger depuis .env
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('TRACKED_ADDRESS='):
                        address = line.split('=', 1)[1].strip()
                        break
                else:
                    print("❌ TRACKED_ADDRESS non trouvé dans .env")
                    sys.exit(1)
        else:
            print("❌ Fichier .env non trouvé")
            sys.exit(1)
    elif args.address:
        address = args.address
    else:
        print("❌ Adresse requise. Utilisez --address ou --from-env")
        sys.exit(1)
    
    print("=" * 60)
    print("RÉCUPÉRATION DES POSITIONS ACTUELLES")
    print("=" * 60)
    print(f"Adresse: {address}")
    
    # Récupérer les positions
    positions = fetch_positions(address)
    if not positions:
        print("❌ Impossible de récupérer les positions")
        sys.exit(1)
    
    # Sauvegarder
    if save_positions(positions):
        print("\n🎉 Positions sauvegardées avec succès !")
        print("🔄 Redémarrez le service pour utiliser les nouvelles données:")
        print("   docker-compose restart dynamic-pairlist")
        
        # Afficher les paires détectées
        print(f"\n📋 Paires détectées ({len(positions)}) :")
        for i, pos in enumerate(positions, 1):
            direction = "LONG" if pos['size'] > 0 else "SHORT"
            print(f"   {i:2d}. {pos['coin']:>12} | {direction:>5} | ${pos['position_value']:>10.2f}")
    else:
        print("❌ Échec de la sauvegarde")
        sys.exit(1)

if __name__ == "__main__":
    main()