# 🚀 TRADING BOT - QUICK START GUIDE

## ⚡ **Get Running in 3 Steps**

---

## 📦 **Step 1: Extract & Install**

```bash
# Extract the archive
unzip trading_bot_final.zip
# or
tar -xzf trading_bot_final.tar.gz

# Go to directory
cd trading_bot_final

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ **Step 2: Configure Telegram**

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
nano .env  # or use any text editor
```

**Add your Telegram credentials:**
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**How to get these:**
1. **Bot Token:** Talk to @BotFather on Telegram → /newbot
2. **Chat ID:** Talk to @userinfobot on Telegram → get your ID

---

## ▶️ **Step 3: Run**

```bash
python main.py
```

**That's it!** Bot will start monitoring for signals! ✅

---

## 📱 **You'll Receive Telegram Alerts Like:**

```
✅ CONFIRMED SIGNAL — BTCUSDT (15m)

💰 Price: $45,120.00 | EMA200: $45,000.00
🚀 EMA Expansion: 0.25%
📈 EMA200 Change: +0.27% since cross
💪 ADX 15m: 27.3 | 1h: 24.1
📊 RSI 15m: 56.2 | 1h: 53.8
📊 Volume at Cross: 5.0x

💎 ALL CRITERIA MET
```

---

## ⚙️ **Configuration (Optional)**

### **Edit `config.py` to customize:**

```python
# Number of coins to monitor
SYMBOL_CONFIG = {
    'top_n_coins': 400,  # Change to 20, 50, 100, etc.
}

# Volume requirement
SIGNAL_CONFIG = {
    'volume_min_ratio': 3.0,  # Change to 2.0, 2.5, etc.
}
```

---

## 🎯 **What This Bot Does:**

### **Monitors for EMA50/200 Crosses:**
- Checks 15m timeframe for crosses
- Verifies trend strength on both 15m and 1h
- Requires ALL criteria to pass

### **8 Compulsory Criteria:**
1. ✅ Price above EMA200
2. ✅ ADX 15m > 25
3. ✅ ADX 1h > 22
4. ✅ RSI 15m > 50
5. ✅ RSI 1h > 50
6. ✅ EMA Expansion > 0.2%
7. ✅ EMA200 Slope Rising
8. ✅ Volume at cross ≥ 3x

**If ANY fails → No signal!**

---

## 📊 **Expected Performance:**

- **Signals:** 3-10 per day (high quality)
- **Quality:** Very strict filtering
- **Speed:** Checks immediately after cross (no wait time)

---

## 🛠️ **Troubleshooting:**

### **"Module not found"**
```bash
pip install -r requirements.txt
```

### **"Telegram not working"**
- Check `.env` has correct token and chat_id
- Click START in your bot chat
- Test: Run bot and wait for startup message

### **"No signals"**
- Normal! Criteria are strict
- Check logs: `tail -f trading_bot.log`
- Look for "Signal REJECTED" to see why

### **Want more signals?**
Edit `config.py`:
```python
'volume_min_ratio': 2.0,  # Lower from 3.0
'expansion_threshold': 0.0015,  # Lower from 0.002
```

---

## 📂 **Files Included:**

```
trading_bot_final/
├── main.py                 ← Run this
├── config.py              ← Configure here
├── .env.example           ← Copy to .env
├── requirements.txt
│
├── Core Modules (13 files):
│   ├── trading_bot.py
│   ├── binance_client.py
│   ├── market_data_manager.py
│   ├── indicators.py
│   ├── cross_detector.py
│   ├── feature_calculator.py
│   ├── scoring_engine.py
│   ├── signal_evaluator.py
│   ├── regime_tracker.py
│   ├── telegram_notifier.py
│   └── models.py
│
└── Documentation (3 files):
    ├── QUICK_START.md (this file)
    ├── CONFIGURATION.md
    └── CHANGELOG.md
```

---

## ✅ **Ready to Go!**

```bash
cd trading_bot_final
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python main.py
```

---

## 🆘 **Need Help?**

Check the other documentation files:
- **CONFIGURATION.md** - Detailed config options
- **CHANGELOG.md** - What's new/changed

---

**Happy Trading!** 🚀💎
