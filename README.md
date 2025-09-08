# Hyperliquid Perp Copy Trading Strategy

A Freqtrade strategy that automatically copies trades from a Hyperliquid perpetual futures (perp) account to your Freqtrade bot.
More about Freqtrade: https://www.freqtrade.io/en/stable/

## Overview

This strategy monitors a specified Hyperliquid wallet address and replicates its perp trading positions in your Freqtrade bot with appropriate position sizing based on account value scaling, and an "effective" leverage asssumption.

**EDIT:** added a Long+Short version `COPY_HL_LS`. You need to edit `docker-compose.yml` and replace `COPY_HL` by `COPY_HL_LS` to use it. Still experimental, use at your own risk.

## Features

- **Real-time Position Tracking**: Monitors target Hyperliquid account for position changes
- **Smart Position Scaling**: Automatically scales position sizes based on account value ratios
- **Position Change Detection**: Detects opens, closes, increases, decreases, and modifications
- **Long-Only Trading**: **Only copies long positions** (ignores shorts for simplicity, and in general it reduces the long-term risk-reward ratio). NEW: added a Long+Short version
- **Comprehensive Logging**: Detailed position summaries and change tracking
- **Data Persistence**: Saves position history and changes to CSV files
- **Missed Trade Recovery**: Detects and corrects missed entries/exits, or incorect sizing
- Can trade top ~50 Hyperliquid coins, sorted by market cap (ignores lower ranked), dynamic list, see full list here : https://remotepairlist.com?q=4885f6046bea5db4

## Requirements

### Dependencies
`docker`, `docker compose`

## Configuration

### Main Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_open_trades` (in `config.json`)| 4 | Maximum number of positions at a given time. **Which value to use will depend on the account you copy**. |
| `LEV` (in `COPY_HL.py`) | 6 | Effective leverage to use. **Which value to use will depend on the account you copy**, and it can be tricky to evaluate (If the trader you’re copying uses cross margin with leverage of 25, that doesn’t mean you should enter 25 here. What really matters is the maximum position size they take relative to their total account value. For example, if you’re following an account with 100k USDC in capital, and at some point you notice they hold positions totaling 300k USDC, that implies you’ll need at least 3x leverage—ideally 4x to be safe. But keep in mind: if you set your leverage value too high, you risk being liquidated on a trade where the copied account would not be) |
| `change_threshold` (in `COPY_HL.py`)| 0.5 | Minimum position size or position change threshold (% of account). Will ignore changes, or positions with sizes below this %. If the trader does a few small changes below 0.5%, the bot will still trigger a position size change (correction) when the relative "error"/difference between the expected and actual position gets above 10% |
| `adjustement_threshold` (in `COPY_HL.py`)| 10 | Tolerated threshold difference % between a target copied position size and my actual position size |
| `ADDRESS_TO_TRACK_TOP` (in `COPY_HL.py`)| Set in code | Hyperliquid wallet address to copy |


Remark: `stake_amount` in `config.json` is ignored.

### Required Settings

1. **Set Target Address**: Update `ADDRESS_TO_TRACK_TOP` variable at the top of `COPY_HL.py` with the Hyperliquid wallet you want to copy, for example:
```python
ADDRESS_TO_TRACK_TOP = "0x95b8b411653328db32f59b143c6d45f8501e2b35"
```
You can also check the positions (verify if they are copied properly) of the wallet to copy with e.g. : https://apexliquid.bot/detail?address=0x95b8b411653328db32f59b143c6d45f8501e2b35

## How It Works

### Position Tracking
1. **API Polling**: Fetches position data from Hyperliquid (cached)
2. **Change Detection**: Compares current positions with previous snapshot
3. **Signal Generation**: Creates buy/sell signals based on detected changes
4. See `track_account.py` to test the account tracking class.

### Position Scaling
- Calculates scale factor: `My Account Value / Copied Account Value`
- Adjusts position sizes proportionally
- Only copies positions >0.5% of copied account value (absolute or changes)

### Trade Management
- **Entry**: Opens positions when target account opens new longs
- **Exit**: Closes positions when target account closes positions
- **Adjustment**: Increases/decreases positions to match target ratios
- **Safety**: Immediately exits any mistakenly opened Short or Long positions

## Position Types Detected

| Change Type | Description | Action |
|-------------|-------------|---------|
| `opened_long` | New long position opened | Enter long |
| `closed` | Position closed | Exit position |
| `increased` | Position size increased | Add to position |
| `decreased` | Position size decreased | Reduce position |
| `modified` | Leverage/entry price changed | None |
| `flipped` | Direction changed (long↔short) | None |

## File Structure

The strategy creates a `position_data/` directory with:
- `positions_history.csv` - Complete position history
- `last_positions.csv` - Current position snapshots  
- `changes_log.csv` - All detected changes

- `show_PnL.py` shows current bot's PnL (all and closed) and metrics, works only if the rest API server is ON and USERNAME and PASSWORD are consistent with values in `config.json` .

## Usage

1. **Install Dependencies**:
`docker`, `docker compose`

2. **Configure Strategy**:
```python
# In `COPY_HL.py`, set your target address
ADDRESS_TO_TRACK_TOP = "0x95b8b411653328db32f59b143c6d45f8501e2b35"
```
Adjust `max_open_trades` (in `config.json`) and `LEV` (in `COPY_HL.py`) for the account to be copied.

3. **Start Freqtrade**: open a terminal in the folder containing the file `docker-compose.yml` and run commands:
```bash
docker compose build
docker compose up
# optionally use 'docker compose up -d' to run as persistent background deamon process
```

## Safety Features

- **Long-Only**: Automatically ignores and closes any short positions
- **Size Limits**: Respects Freqtrade's min/max stake amounts
- **Error Handling**: Gracefully handles API failures and data issues
- **Position Validation**: Continuously validates position alignment
- **Threshold Protection**: Ignores insignificant positions or positions changes

## Monitoring

### Console Output
The strategy provides detailed logging including:
- Position change summaries
- Account value comparisons
- Scale factor calculations
- Position matching analysis
- Missing/extra position alerts

### Example Log
```
================================================================================
POSITIONS SUMMARY
================================================================================
Copied Account Value: $2,054,213.79
My Account Value:    $1,085.99
Scale Factor:        0.000529x (inverted 1891.6x )
--------------------------------------------------
POSITIONS TO COPY:
       ETH |  LONG | Size:       0.0059 | Value: $     26.45 ( 0.00%) | Scaled: $      0.01
       LTC |  LONG | Size:   18345.1600 | Value: $2023287.70 (98.49%) | Scaled: $   1069.64
      HYPE |  LONG | Size:  133827.7300 | Value: $5933252.41 (288.83%) | Scaled: $   3136.70
      WLFI |  LONG | Size: 6484884.0000 | Value: $1440876.38 (70.14%) | Scaled: $    761.74
--------------------------------------------------
MY OPEN POSITIONS:
      HYPE | LONG  | Stake: $    496.94 | Value: $   2981.67 (274.56%) | Leverage: 6.0x
       LTC | LONG  | Stake: $    174.56 | Value: $   1047.39 (96.45%) | Leverage: 6.0x
--------------------------------------------------
POSITION MATCHING ANALYSIS:
  Matching positions:
        HYPE | Copied: $5933252.41 -> Expected: $ 3136.70 | Actual: $ 2981.67 | Diff:   -4.9%
         LTC | Copied: $2023287.70 -> Expected: $ 1069.64 | Actual: $ 1047.39 | Diff:   -2.1%
  Missing positions (should open if in whitelist):
        WLFI |  LONG | Copied $1440876.38 (70.14% of copied) | Expected scaled: $  761.74 (70.14% of mine) ✓ , not in whitelist
================================================================================
HYPE → Difference: -4.94%   (my total value: 2981.7) ; ||>10% will trigger a size correction.
LTC → Difference: -2.08%   (my total value: 1047.4) ; ||>10% will trigger a size correction.
```

## Disclaimers

⚠️ **Important Warnings**:
- Very fresh and experimental, use with Dry-run only (paper trading)
- Monitor positions regularly (e.g. look in `https://apexliquid.bot/`)
- The copied trader's strategy may not be suitable for your risk tolerance and leverage level
- Past performance doesn't guarantee future results

## License

This strategy is provided as-is for educational purposes. Use at your own risk.
