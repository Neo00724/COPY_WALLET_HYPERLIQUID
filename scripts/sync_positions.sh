#!/bin/bash

# Script de synchronisation des positions pour le service de paires dynamiques
# À exécuter après chaque redémarrage ou suppression des données

echo "🔄 Synchronisation des positions du compte copié..."

# Vérifier que Docker est en cours d'exécution
if ! docker-compose ps | grep -q "freqtrade.*Up"; then
    echo "❌ FreqTrade n'est pas en cours d'exécution"
    echo "💡 Démarrez d'abord avec: docker-compose up -d"
    exit 1
fi

# Récupérer les positions depuis le container FreqTrade
echo "📡 Récupération des positions actuelles..."
docker-compose exec -T freqtrade python3 -c "
import os
import csv
from datetime import datetime
from hyperliquid.info import Info
from hyperliquid.utils import constants

address = os.getenv('TRACKED_ADDRESS', '0xe61c2251b2641989f49bb5b73b2a8d0dbc6e40d8')
data_dir = '/freqtrade/user_data/strategies/position_data'

try:
    os.makedirs(data_dir, exist_ok=True)
    
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    perp_data = info.user_state(address)
    
    positions = []
    timestamp = perp_data.get('time', int(datetime.now().timestamp() * 1000))
    human_time = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
    
    for asset_pos in perp_data.get('assetPositions', []):
        if asset_pos['type'] == 'oneWay' and 'position' in asset_pos:
            pos = asset_pos['position']
            size = float(pos['szi'])
            if size != 0:
                leverage_value = pos['leverage']['value'] if isinstance(pos['leverage'], dict) else pos['leverage']
                positions.append({
                    'coin': pos['coin'],
                    'size': size,
                    'entry_price': float(pos['entryPx']),
                    'position_value': float(pos['positionValue']),
                    'unrealized_pnl': float(pos['unrealizedPnl']),
                    'leverage': float(leverage_value),
                    'margin_used': float(pos['marginUsed']),
                    'timestamp': timestamp,
                    'human_time': human_time
                })
    
    # Sauvegarder last_positions.csv
    with open(f'{data_dir}/last_positions.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['coin', 'size', 'entry_price', 'position_value', 'unrealized_pnl', 'leverage', 'margin_used', 'timestamp', 'human_time'])
        for pos in positions:
            writer.writerow([pos['coin'], pos['size'], pos['entry_price'], pos['position_value'], pos['unrealized_pnl'], pos['leverage'], pos['margin_used'], pos['timestamp'], pos['human_time']])
    
    # Sauvegarder changes_log.csv
    with open(f'{data_dir}/changes_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['coin', 'change_type', 'old_size', 'new_size', 'old_position_value', 'new_position_value', 'timestamp', 'human_time'])
        for pos in positions:
            position_type = 'long' if pos['size'] > 0 else 'short'
            writer.writerow([pos['coin'], f'opened_{position_type}', '', pos['size'], '', pos['position_value'], pos['timestamp'], pos['human_time']])
    
    print(f'✅ {len(positions)} positions synchronisées')
    
except Exception as e:
    print(f'❌ Erreur: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "🔄 Redémarrage du service de paires..."
    docker-compose restart dynamic-pairlist
    
    echo "⏳ Attente du redémarrage..."
    sleep 5
    
    echo "🔄 Redémarrage de FreqTrade pour récupérer les nouvelles paires..."
    docker-compose restart freqtrade
    
    echo "⏳ Attente du redémarrage de FreqTrade..."
    sleep 10
    
    echo "✅ Synchronisation terminée !"
    echo ""
    echo "📊 Vérification des résultats:"
    echo "   - Service de paires: curl http://localhost:5001/pairlist"
    echo "   - Logs FreqTrade: docker-compose logs freqtrade | grep 'Whitelist with'"
    echo ""
    
    # Afficher le résultat
    echo "🎯 Paires générées par le service:"
    curl -s http://localhost:5001/pairlist | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    pairs = data.get('pairs', [])
    print(f'   Total: {len(pairs)} paires')
    for i, pair in enumerate(pairs, 1):
        coin = pair.split('/')[0]
        print(f'   {i:2d}. {coin}')
except:
    print('   Erreur lors de la lecture des paires')
"
else
    echo "❌ Échec de la synchronisation"
    exit 1
fi