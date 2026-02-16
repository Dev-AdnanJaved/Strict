# ⚙️ CONFIGURATION GUIDE

## 📋 **All Settings in `config.py`**

---

## 🎯 **Symbol Selection**

```python
SYMBOL_CONFIG = {
    'mode': 'top_volume',        # 'top_volume', 'all', or 'custom'
    'top_n_coins': 400,          # How many coins to monitor
    'min_volume_filter': 0,       # Minimum 24h volume (0 = no filter)
    'custom_symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],  # If mode='custom'
}
```

### **Options:**

**Mode: 'top_volume' (Recommended)**
- Monitors top N coins by 24h volume
- Auto-updates list dynamically
```python
'mode': 'top_volume',
'top_n_coins': 20,  # Monitor top 20
```

**Mode: 'custom'**
- Monitor specific coins only
```python
'mode': 'custom',
'custom_symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
```

**Mode: 'all'**
- Monitors ALL USDT pairs (not recommended - too many)

---

## 🔍 **Signal Detection Settings**

```python
SIGNAL_CONFIG = {
    # Cross Detection
    'cross_emas': [50, 200],
    'cross_lookback': 5,
    'evaluation_window': 96,  # 24 hours on 15m
    
    # Multi-Timeframe ADX (COMPULSORY)
    'adx_threshold_15m': 25,
    'adx_threshold_1h': 22,
    
    # Multi-Timeframe RSI (COMPULSORY)
    'rsi_threshold_15m': 50,
    'rsi_threshold_1h': 50,
    
    # Structure (Optional - not checked)
    'structure_lookback': 5,
    'structure_min_holds': 2,
    
    # Reclaim (Optional - not checked)
    'reclaim_lookback': 4,
    
    # EMA Expansion (COMPULSORY)
    'expansion_threshold': 0.002,  # 0.2%
    
    # Volume (COMPULSORY)
    'volume_cross_window': 2,      # ±2 candles
    'volume_baseline_period': 50,  # 50 candle baseline
    'volume_min_ratio': 3.0,       # 3x required
}
```

---

## 🎛️ **Adjustable Parameters:**

### **1. Volume Requirement**

**Current: 3.0x**
```python
'volume_min_ratio': 3.0,  # Very strict
```

**Options:**
```python
'volume_min_ratio': 2.0,  # More signals (moderate)
'volume_min_ratio': 2.5,  # Balanced
'volume_min_ratio': 3.0,  # Fewer signals (strict)
'volume_min_ratio': 4.0,  # Very few signals (very strict)
```

**Impact:**
- Lower = More signals (easier to pass)
- Higher = Fewer signals (harder to pass)

---

### **2. ADX Thresholds**

**Current: 15m=25, 1h=22**
```python
'adx_threshold_15m': 25,
'adx_threshold_1h': 22,
```

**Options:**
```python
# More signals (weaker trends)
'adx_threshold_15m': 20,
'adx_threshold_1h': 18,

# Balanced (current)
'adx_threshold_15m': 25,
'adx_threshold_1h': 22,

# Fewer signals (stronger trends)
'adx_threshold_15m': 30,
'adx_threshold_1h': 25,
```

---

### **3. EMA Expansion**

**Current: 0.2%**
```python
'expansion_threshold': 0.002,  # 0.2%
```

**Options:**
```python
'expansion_threshold': 0.001,  # 0.1% - easier
'expansion_threshold': 0.0015, # 0.15% - moderate
'expansion_threshold': 0.002,  # 0.2% - strict (current)
'expansion_threshold': 0.003,  # 0.3% - very strict
```

**Example (BTC at $45,000):**
- 0.1% = $45 separation
- 0.2% = $90 separation (current)
- 0.3% = $135 separation

---

### **4. Number of Coins**

**Current: 400**
```python
'top_n_coins': 400,
```

**Options:**
```python
'top_n_coins': 10,   # Only majors
'top_n_coins': 20,   # Top 20
'top_n_coins': 50,   # Good balance
'top_n_coins': 100,  # More opportunities
'top_n_coins': 400,  # Maximum coverage (current)
```

**Impact:**
- Fewer coins = Fewer signals, more focused
- More coins = More signals, broader coverage

---

### **5. Volume Baseline Period**

**Current: 50 candles**
```python
'volume_baseline_period': 50,
```

**Options:**
```python
'volume_baseline_period': 20,   # Less stable (easier to pass)
'volume_baseline_period': 50,   # Balanced (current)
'volume_baseline_period': 100,  # Very stable (stricter)
```

---

## 🎯 **Preset Configurations:**

### **Conservative (Fewer, High-Quality Signals)**
```python
SYMBOL_CONFIG = {
    'top_n_coins': 20,
}

SIGNAL_CONFIG = {
    'adx_threshold_15m': 28,
    'adx_threshold_1h': 25,
    'rsi_threshold_15m': 52,
    'rsi_threshold_1h': 52,
    'expansion_threshold': 0.003,  # 0.3%
    'volume_min_ratio': 3.5,       # 3.5x
    'volume_baseline_period': 100,
}
```
**Expected: 1-5 signals/day**

---

### **Balanced (Current Settings)**
```python
SYMBOL_CONFIG = {
    'top_n_coins': 400,
}

SIGNAL_CONFIG = {
    'adx_threshold_15m': 25,
    'adx_threshold_1h': 22,
    'rsi_threshold_15m': 50,
    'rsi_threshold_1h': 50,
    'expansion_threshold': 0.002,  # 0.2%
    'volume_min_ratio': 3.0,
    'volume_baseline_period': 50,
}
```
**Expected: 3-10 signals/day**

---

### **Aggressive (More Signals)**
```python
SYMBOL_CONFIG = {
    'top_n_coins': 400,
}

SIGNAL_CONFIG = {
    'adx_threshold_15m': 22,
    'adx_threshold_1h': 20,
    'rsi_threshold_15m': 50,
    'rsi_threshold_1h': 50,
    'expansion_threshold': 0.0015,  # 0.15%
    'volume_min_ratio': 2.0,        # 2x
    'volume_baseline_period': 50,
}
```
**Expected: 7-20 signals/day**

---

## 📱 **Telegram Settings**

```python
TELEGRAM_CONFIG = {
    'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
    'chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
    'enable_notifications': True,
}
```

**Set in `.env` file:**
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

---

## 🔄 **Runtime Settings**

**In `main.py`:**
```python
runner = BotRunner(
    run_interval=60  # Check every 60 seconds
)
```

**Change interval:**
```python
run_interval=30   # Check every 30 seconds (more frequent)
run_interval=120  # Check every 2 minutes (less frequent)
```

---

## 🎯 **Optimization Tips:**

### **Getting Too Few Signals?**
1. Lower volume requirement: 3.0 → 2.0
2. Lower expansion: 0.002 → 0.0015
3. Lower ADX: 25/22 → 22/20
4. Increase coins: 20 → 100

### **Getting Too Many False Signals?**
1. Increase volume: 3.0 → 4.0
2. Increase expansion: 0.002 → 0.003
3. Increase ADX: 25/22 → 28/25
4. Decrease coins: 400 → 50

### **Want Only Major Coins?**
```python
SYMBOL_CONFIG = {
    'mode': 'custom',
    'custom_symbols': [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT',
        'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT'
    ],
}
```

---

## ✅ **Recommended Starting Point:**

**For Most Users:**
```python
SYMBOL_CONFIG = {
    'top_n_coins': 50,  # Good balance
}

SIGNAL_CONFIG = {
    'volume_min_ratio': 2.5,  # Not too strict
}
```

**Then adjust based on:**
- How many signals you're getting
- Quality of signals
- Your risk tolerance

---

## 📊 **Understanding the Settings:**

| Setting | Low Value | High Value |
|---------|-----------|------------|
| top_n_coins | Fewer signals | More signals |
| volume_min_ratio | More signals | Fewer signals |
| adx_threshold | More signals | Fewer signals |
| expansion_threshold | More signals | Fewer signals |

**General Rule:**
- Want more signals? → Lower thresholds
- Want better quality? → Raise thresholds

---

**Start with defaults, run for a day, then adjust!** 🎯
