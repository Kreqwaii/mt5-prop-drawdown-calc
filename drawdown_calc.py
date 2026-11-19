#!/usr/bin/env python3
"""
MT5 Prop Firm Drawdown & Lot Size Calculator (Free OSS Lite Edition)
Zero-dependency Python 3 CLI calculator for FTMO, FundedNext, The5ers, and Apex traders.

Calculates:
  - Exact USD risk per trade and safe floored lot size (0.01 step)
  - Daily drawdown dollar allowance & remaining daily buffer
  - Max drawdown dollar allowance & remaining total buffer
  - Max consecutive full Stop-Loss trades before breach
  - Risk-of-breach warnings tailored to prop firm limits

License: MIT
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

PROP_FIRM_PRESETS: dict[str, dict[str, Any]] = {
    "ftmo": {
        "label": "FTMO",
        "daily_dd_pct": 5.0,
        "max_dd_pct": 10.0,
        "notes": "5% daily loss (equity/balance based at 00:00 CE(S)T reset), 10% max static loss.",
    },
    "fundednext": {
        "label": "FundedNext",
        "daily_dd_pct": 5.0,
        "max_dd_pct": 10.0,
        "notes": "5% daily loss limit, 10% max loss limit (verify challenge type: Stellar/Evaluation).",
    },
    "the5ers": {
        "label": "The5ers",
        "daily_dd_pct": 5.0,
        "max_dd_pct": 10.0,
        "notes": "High Stakes default: 5% daily pause/loss, 10% max stop-out (Bootcamp/Hyper differ).",
    },
    "apex": {
        "label": "Apex Trader Funding",
        "daily_dd_pct": 3.0,
        "max_dd_pct": 6.0,
        "notes": "Watch intraday trailing drawdown threshold carefully; conservative 3% daily cap recommended.",
    },
    "custom": {
        "label": "Custom Prop Rules",
        "daily_dd_pct": 5.0,
        "max_dd_pct": 10.0,
        "notes": "User-supplied daily and maximum drawdown limits.",
    },
}


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def floor_to_step(value: float, step: float = 0.01) -> float:
    """Floor lot size safely to broker step (e.g. 0.01) so actual risk never exceeds target."""
    if value <= 0 or step <= 0:
        return 0.0
    units = math.floor((value + 1e-12) / step)
    return round(units * step, 4)


def calculate_prop_risk(
    *,
    balance: float,
    risk_pct: float,
    sl_pips: float,
    daily_dd_pct: float,
    max_dd_pct: float = 10.0,
    pip_value_per_lot: float = 10.0,
    equity: float | None = None,
    start_day_balance: float | None = None,
    firm: str = "ftmo",
    lot_step: float = 0.01,
    min_lot: float = 0.01,
) -> dict[str, Any]:
    """Compute position sizing, drawdown limits, buffers, and breach thresholds."""
    if balance <= 0:
        raise ValueError("--balance must be greater than 0")
    if risk_pct <= 0 or risk_pct > 100:
        raise ValueError("--risk-pct must be in (0, 100]")
    if sl_pips <= 0:
        raise ValueError("--sl-pips must be greater than 0")
    if daily_dd_pct <= 0 or daily_dd_pct > 100:
        raise ValueError("--daily-dd must be in (0, 100]")
    if max_dd_pct <= 0 or max_dd_pct > 100:
        raise ValueError("--max-dd must be in (0, 100]")
    if pip_value_per_lot <= 0:
        raise ValueError("--pip-value must be greater than 0")

    current_equity = balance if equity is None else equity
    day_anchor = balance if start_day_balance is None else start_day_balance

    risk_usd = balance * (risk_pct / 100.0)
    raw_lots = risk_usd / (sl_pips * pip_value_per_lot)
    recommended_lots = floor_to_step(raw_lots, lot_step)
    below_min_lot = recommended_lots < min_lot

    actual_risk_usd = recommended_lots * sl_pips * pip_value_per_lot
    actual_risk_pct = (actual_risk_usd / balance) * 100.0

    # Drawdown calculations
    daily_dd_limit_usd = day_anchor * (daily_dd_pct / 100.0)
    daily_loss_so_far_usd = max(0.0, day_anchor - current_equity)
    daily_remaining_usd = max(0.0, daily_dd_limit_usd - daily_loss_so_far_usd)
    daily_remaining_pct = (daily_remaining_usd / day_anchor) * 100.0 if day_anchor > 0 else 0.0

    max_dd_limit_usd = balance * (max_dd_pct / 100.0)
    total_loss_so_far_usd = max(0.0, balance - current_equity)
    max_remaining_usd = max(0.0, max_dd_limit_usd - total_loss_so_far_usd)
    max_remaining_pct = (max_remaining_usd / balance) * 100.0

    if actual_risk_usd > 0:
        losses_to_daily_breach = math.floor(daily_remaining_usd / actual_risk_usd)
        losses_to_max_breach = math.floor(max_remaining_usd / actual_risk_usd)
    else:
        losses_to_daily_breach = 0
        losses_to_max_breach = 0

    warnings: list[str] = []
    status = "SAFE"

    if daily_remaining_usd <= 0 or max_remaining_usd <= 0:
        status = "BREACHED"
        warnings.append("Account equity is already at or beyond the configured drawdown limit!")
    elif below_min_lot:
        status = "CAUTION"
        warnings.append(
            f"Raw lot size ({raw_lots:.4f}) is below minimum {min_lot:.2f} lot; "
            "reduce --balance target check, widen risk, or tighten SL."
        )
    elif actual_risk_usd > daily_remaining_usd:
        status = "DANGER"
        warnings.append(
            f"A single Stop-Loss (${actual_risk_usd:,.2f}) exceeds remaining Daily DD buffer (${daily_remaining_usd:,.2f})!"
        )
    elif losses_to_daily_breach < 2:
        status = "DANGER"
        warnings.append(
            f"Only {losses_to_daily_breach} full SL trade(s) left before hitting Daily DD limit."
        )
    elif risk_pct > 2.0 or risk_pct > (daily_dd_pct * 0.4):
        status = "CAUTION"
        warnings.append(
            f"Risk per trade ({risk_pct:.2f}%) is aggressive relative to {daily_dd_pct:.2f}% Daily DD."
        )

    preset = PROP_FIRM_PRESETS.get(firm, PROP_FIRM_PRESETS["custom"])

    return {
        "firm": firm,
        "firm_label": preset["label"],
        "firm_notes": preset["notes"],
        "inputs": {
            "balance": round(balance, 2),
            "equity": round(current_equity, 2),
            "start_day_balance": round(day_anchor, 2),
            "risk_pct": round(risk_pct, 4),
            "sl_pips": round(sl_pips, 2),
            "pip_value_per_lot": round(pip_value_per_lot, 4),
            "daily_dd_pct": round(daily_dd_pct, 2),
            "max_dd_pct": round(max_dd_pct, 2),
        },
        "sizing": {
            "target_risk_usd": round(risk_usd, 2),
            "raw_lots": round(raw_lots, 4),
            "recommended_lots": round(recommended_lots, 2),
            "actual_risk_usd": round(actual_risk_usd, 2),
            "actual_risk_pct": round(actual_risk_pct, 4),
        },
        "drawdown": {
            "daily_dd_limit_usd": round(daily_dd_limit_usd, 2),
            "daily_loss_so_far_usd": round(daily_loss_so_far_usd, 2),
            "daily_remaining_usd": round(daily_remaining_usd, 2),
            "daily_remaining_pct": round(daily_remaining_pct, 2),
            "max_dd_limit_usd": round(max_dd_limit_usd, 2),
            "total_loss_so_far_usd": round(total_loss_so_far_usd, 2),
            "max_remaining_usd": round(max_remaining_usd, 2),
            "max_remaining_pct": round(max_remaining_pct, 2),
            "losses_to_daily_breach": losses_to_daily_breach,
            "losses_to_max_breach": losses_to_max_breach,
        },
        "health": {
            "status": status,
            "warnings": warnings,
        },
    }


def run_self_test() -> int:
    """Run deterministic self-tests for prop firm lot sizing and drawdown math."""
    print("[SELF-TEST] Running mt5-prop-drawdown-calc verification suite...")
    failures: list[str] = []

    # Case 1: Classic $100,000 FTMO account, 1% risk, 20 pip SL, $10/pip/lot -> 5.00 lots
    res1 = calculate_prop_risk(
        balance=100_000.0,
        risk_pct=1.0,
        sl_pips=20.0,
        daily_dd_pct=5.0,
        max_dd_pct=10.0,
        pip_value_per_lot=10.0,
        firm="ftmo",
    )
    if (
        res1["sizing"]["recommended_lots"] != 5.0
        or res1["sizing"]["actual_risk_usd"] != 1000.0
        or res1["drawdown"]["daily_dd_limit_usd"] != 5000.0
        or res1["drawdown"]["losses_to_daily_breach"] != 5
        or res1["health"]["status"] != "SAFE"
    ):
        failures.append(f"Case 1 mismatch: {res1}")
    else:
        print("  [PASS] Case 1: $100k FTMO 1% risk / 20 SL -> 5.00 lots, 5 SL losses to daily breach")

    # Case 2: Flooring protection ($10,000 balance, 0.5% risk = $50, 17 pips SL -> raw 0.2941 -> 0.29 lots)
    res2 = calculate_prop_risk(
        balance=10_000.0,
        risk_pct=0.5,
        sl_pips=17.0,
        daily_dd_pct=5.0,
        firm="fundednext",
    )
    if res2["sizing"]["recommended_lots"] != 0.29 or res2["sizing"]["actual_risk_usd"] > 50.0:
        failures.append(f"Case 2 flooring mismatch: {res2['sizing']}")
    else:
        print("  [PASS] Case 2: Safe lot flooring to 0.01 step without exceeding target risk")

    # Case 3: Near-breach warning when equity already lost $4,200 out of $5,000 daily DD
    res3 = calculate_prop_risk(
        balance=100_000.0,
        equity=95_800.0,
        start_day_balance=100_000.0,
        risk_pct=1.0,
        sl_pips=25.0,
        daily_dd_pct=5.0,
        firm="the5ers",
    )
    if res3["health"]["status"] != "DANGER" or res3["drawdown"]["daily_remaining_usd"] != 800.0:
        failures.append(f"Case 3 danger detection mismatch: {res3}")
    else:
        print("  [PASS] Case 3: DANGER flag triggered when 1 SL ($1,000) > remaining $800 daily buffer")

    # Case 4: Invalid input guard
    try:
        calculate_prop_risk(balance=-500, risk_pct=1.0, sl_pips=10.0, daily_dd_pct=5.0)
        failures.append("Case 4 failed: negative balance did not raise ValueError")
    except ValueError:
        print("  [PASS] Case 4: Negative/invalid balance validation")

    if failures:
        print("\n[SELF-TEST FAILED]")
        for err in failures:
            print(f"  - {err}")
        return 1

    print("\n[SELF-TEST PASSED] 100% PASS (all calculations verified).")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drawdown_calc.py",
        description="Free MT5 Prop Firm Drawdown & Lot Size Calculator (FTMO / FundedNext / The5ers / Apex).",
    )
    parser.add_argument(
        "--firm",
        choices=sorted(PROP_FIRM_PRESETS.keys()),
        default="ftmo",
        help="Prop firm preset (default: ftmo)",
    )
    parser.add_argument("--balance", type=float, default=100_000.0, help="Account balance in USD (default: 100000)")
    parser.add_argument("--equity", type=float, default=None, help="Current floating equity (defaults to --balance)")
    parser.add_argument(
        "--start-day-balance",
        type=float,
        default=None,
        help="Start-of-day balance/equity anchor for Daily DD (defaults to --balance)",
    )
    parser.add_argument("--risk-pct", type=float, default=1.0, help="Risk per trade in %% (default: 1.0)")
    parser.add_argument("--sl-pips", type=float, default=20.0, help="Stop-Loss distance in pips (default: 20)")
    parser.add_argument(
        "--pip-value",
        type=float,
        default=10.0,
        help="Pip value per 1.00 standard lot in USD (default: 10.0 for EURUSD/GBPUSD)",
    )
    parser.add_argument(
        "--daily-dd",
        type=float,
        default=None,
        help="Daily Drawdown limit in %% (defaults to preset, e.g. 5.0)",
    )
    parser.add_argument(
        "--max-dd",
        type=float,
        default=None,
        help="Max Total Drawdown limit in %% (defaults to preset, e.g. 10.0)",
    )
    parser.add_argument("--json", action="store_true", help="Output calculation result as JSON")
    parser.add_argument("--self-test", action="store_true", help="Run built-in self-tests and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    preset = PROP_FIRM_PRESETS[args.firm]
    daily_dd = args.daily_dd if args.daily_dd is not None else float(preset["daily_dd_pct"])
    max_dd = args.max_dd if args.max_dd is not None else float(preset["max_dd_pct"])

    try:
        res = calculate_prop_risk(
            balance=args.balance,
            risk_pct=args.risk_pct,
            sl_pips=args.sl_pips,
            daily_dd_pct=daily_dd,
            max_dd_pct=max_dd,
            pip_value_per_lot=args.pip_value,
            equity=args.equity,
            start_day_balance=args.start_day_balance,
            firm=args.firm,
        )
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    inp = res["inputs"]
    sz = res["sizing"]
    dd = res["drawdown"]
    hl = res["health"]

    print("=" * 66)
    print(f"  MT5 Prop Firm Drawdown & Lot Calculator  [{res['firm_label']}]")
    print("=" * 66)
    print(f"Balance / Equity   : ${inp['balance']:,.2f} / ${inp['equity']:,.2f}")
    print(f"Risk Target        : {inp['risk_pct']:.2f}% (${sz['target_risk_usd']:,.2f})")
    print(f"Stop-Loss / PipVal : {inp['sl_pips']:.1f} pips @ ${inp['pip_value_per_lot']:.2f}/pip/lot")
    print("-" * 66)
    print(f"Recommended Lot    : {sz['recommended_lots']:.2f} lots  (exact raw: {sz['raw_lots']:.4f})")
    print(f"Actual Trade Risk  : ${sz['actual_risk_usd']:,.2f} ({sz['actual_risk_pct']:.3f}%)")
    print("-" * 66)
    print(
        f"Daily DD ({inp['daily_dd_pct']:.1f}%)     : Limit ${dd['daily_dd_limit_usd']:,.2f} | "
        f"Remaining ${dd['daily_remaining_usd']:,.2f} ({dd['daily_remaining_pct']:.2f}%)"
    )
    print(
        f"Max DD   ({inp['max_dd_pct']:.1f}%)    : Limit ${dd['max_dd_limit_usd']:,.2f} | "
        f"Remaining ${dd['max_remaining_usd']:,.2f} ({dd['max_remaining_pct']:.2f}%)"
    )
    print(
        f"Survival Runway    : {dd['losses_to_daily_breach']} SL(s) to Daily Breach | "
        f"{dd['losses_to_max_breach']} SL(s) to Max Breach"
    )
    print("-" * 66)
    print(f"Risk Status        : {hl['status']}")
    for warn in hl["warnings"]:
        print(f"  [!] {warn}")
    print(f"Rule Note          : {res['firm_notes']}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
