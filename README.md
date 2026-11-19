# MT5 Prop Firm Drawdown & Lot Size Calculator (Free OSS Lite Edition)

Zero-dependency Python 3 CLI calculator for **FTMO**, **FundedNext**, **The5ers**, and **Apex** prop-firm traders. Instantly compute safe floored lot sizes (`0.01` step), exact risk in USD, daily/max drawdown buffers, and consecutive Stop-Loss survival runway.

Keywords: `MT5`, `Prop Firm`, `FTMO`, `FundedNext`, `The5ers`, `Apex`, `Drawdown Calculator`, `Lot Size Calculator`, `Risk Management`

---

## English Documentation

### Features
- **Safe Lot Sizing (`0.01` floor):** Prevents accidental over-risking when dividing dollar risk by Stop-Loss pips.
- **Built-in Prop Presets:** `ftmo`, `fundednext`, `the5ers`, `apex`, or `custom`.
- **Live Equity & Start-of-Day Anchor Support:** Check how many full Stop-Loss trades remain before breaching your daily or max drawdown rule.
- **Zero external dependencies:** Pure Python 3 stdlib, verified with `--self-test`.

### Usage Examples
```bash
# FTMO $100,000 challenge, 1% risk, 20 pips SL, 5% daily DD
python drawdown_calc.py --firm ftmo --balance 100000 --risk-pct 1.0 --sl-pips 20 --daily-dd 5.0

# FundedNext $50,000 account with floating drawdown ($48,400 equity)
python drawdown_calc.py --firm fundednext --balance 50000 --equity 48400 --risk-pct 0.5 --sl-pips 15 --daily-dd 5.0

# JSON output for scripts or bots
python drawdown_calc.py --balance 100000 --risk-pct 1 --sl-pips 25 --daily-dd 5 --json

# Run built-in self-tests
python drawdown_calc.py --self-test
```

---

### Want Live 24/7 Automated MT5 Protection + Telegram `/panic` Kill-Switch?

Manual calculators can't close runaway trades when spreads spike during NFP or when you step away from your desk. If you want **automated 24/7 MetaTrader 5 prop-firm equity protection**:
- Real-time MT5 equity & floating PnL monitor (`Prop Firm Risk Guard`)
- Automatic **Hard Daily Drawdown & Max Drawdown Auto-Close** before prop firm breach
- Instant **Telegram `/panic` Kill-Switch** (close all open positions & cancel pending orders from your phone)
- News/spread guard & Telegram alert notifications

👉 **Get Prop Firm Risk Guard (Instant Auto-Delivery on FunPay):**
- EN: https://funpay.com/en/lots/offer?id=82596163
- RU: https://funpay.com/lots/offer?id=82596163

---

## Документация на русском (RU)

### Возможности бесплатного калькулятора
- **Безопасный расчёт лота (округление вниз до `0.01`):** вы никогда не превысите заданный процент риска.
- **Пресеты популярных проп-фирм:** `ftmo`, `fundednext`, `the5ers`, `apex` и `custom`.
- **Учёт текущей просадки (`--equity`):** показывает точный остаток дневного и общего лимита в USD и количество стоп-лоссов до слива счёта.
- **Без сторонних зависимостей:** работает на чистом Python 3 из коробки (`--self-test` включён).

### Примеры запуска
```bash
# Расчёт для FTMO $100,000, риск 1%, стоп 20 пипсов, дневной лимит 5%
python drawdown_calc.py --firm ftmo --balance 100000 --risk-pct 1.0 --sl-pips 20 --daily-dd 5.0

# Проверка с учётом текущей просадки
python drawdown_calc.py --balance 50000 --equity 48500 --risk-pct 0.5 --sl-pips 15 --daily-dd 5.0

# Самопроверка математики калькулятора
python drawdown_calc.py --self-test
```

### Нужна автоматическая защита счёта MT5 24/7 + Telegram `/panic` Kill-Switch?

Калькулятор считает лот до входа, но не спасёт депозит, если во время новостей или серии убытков вы не успеете закрыть ордера. Забирайте готового защитника **Prop Firm Risk Guard** с автовыдачей:
- Автоматическое закрытие всех позиций при подходе к дневной или общей просадке MT5
- Мгновенная кнопка **`/panic`** в Telegram для экстренного закрытия всего счёта с телефона
- EN: https://funpay.com/en/lots/offer?id=82596163
- RU: https://funpay.com/lots/offer?id=82596163
