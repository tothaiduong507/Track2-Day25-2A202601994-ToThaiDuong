"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}
REASONING_OUTPUT_MULTIPLIER = 6
REASONING_TARGET_SHARE = 0.05


def _optimized_request_cost(row: dict, output_tokens: int | None = None) -> float:
    """Price one request using its optimized route, cache and batch settings."""
    inp = int(num(row["input_tokens"]))
    out = int(num(row["output_tokens"])) if output_tokens is None else output_tokens
    pin, pout = MODEL_PRICES[row["route_tier"]]
    return pricing.request_cost(
        inp,
        out,
        pin,
        pout,
        cached_in=int(num(row["cached_input_tokens"])),
        batch=bool(int(num(row["is_batch"]))),
    )


def analyze_reasoning_budget(rows: list[dict], target_share: float = REASONING_TARGET_SHARE) -> dict:
    """Measure reasoning cost/energy and simulate a governed traffic cap.

    ``input_tokens`` is used as a reproducible complexity proxy: when the current
    reasoning share exceeds the cap, the largest prompts retain reasoning and the
    remainder fall back to a normal response (one sixth as many output tokens,
    matching the synthetic data generator's reasoning multiplier).
    """
    total_requests = len(rows)
    reasoning_rows = [r for r in rows if bool(int(num(r["is_reasoning"])))]
    normal_rows = [r for r in rows if not bool(int(num(r["is_reasoning"])))]

    reasoning_cost = sum(_optimized_request_cost(r) for r in reasoning_rows)
    normal_cost = sum(_optimized_request_cost(r) for r in normal_rows)
    reasoning_wh = sum(
        sustainability.wh_per_query(
            int(num(r["input_tokens"])) + int(num(r["output_tokens"])),
            is_reasoning=True,
        )
        for r in reasoning_rows
    )
    normal_wh = sum(
        sustainability.wh_per_query(
            int(num(r["input_tokens"])) + int(num(r["output_tokens"])),
            is_reasoning=False,
        )
        for r in normal_rows
    )

    capped_count = min(len(reasoning_rows), max(0, int(total_requests * target_share)))
    ranked = sorted(reasoning_rows, key=lambda r: int(num(r["input_tokens"])), reverse=True)
    downgraded = ranked[capped_count:]
    projected_cost = reasoning_cost + normal_cost
    projected_wh = reasoning_wh + normal_wh
    for r in downgraded:
        original_out = int(num(r["output_tokens"]))
        normal_out = max(1, round(original_out / REASONING_OUTPUT_MULTIPLIER))
        projected_cost += _optimized_request_cost(r, normal_out) - _optimized_request_cost(r)
        projected_wh += sustainability.wh_per_query(
            int(num(r["input_tokens"])) + normal_out,
            is_reasoning=False,
        ) - sustainability.wh_per_query(
            int(num(r["input_tokens"])) + original_out,
            is_reasoning=True,
        )

    current_cost = reasoning_cost + normal_cost
    current_wh = reasoning_wh + normal_wh
    return {
        "total_requests": total_requests,
        "reasoning_requests": len(reasoning_rows),
        "reasoning_traffic_pct": round(len(reasoning_rows) / total_requests * 100, 2) if total_requests else 0.0,
        "reasoning_cost_daily": round(reasoning_cost, 4),
        "reasoning_cost_pct": round(reasoning_cost / current_cost * 100, 2) if current_cost else 0.0,
        "reasoning_energy_wh_daily": round(reasoning_wh, 2),
        "reasoning_energy_pct": round(reasoning_wh / current_wh * 100, 2) if current_wh else 0.0,
        "normal_cost_daily": round(normal_cost, 4),
        "normal_energy_wh_daily": round(normal_wh, 2),
        "target_traffic_pct": round(target_share * 100, 2),
        "retained_reasoning_requests": capped_count,
        "downgraded_requests": len(downgraded),
        "projected_cost_daily": round(projected_cost, 4),
        "projected_energy_wh_daily": round(projected_wh, 2),
        "incremental_cost_savings_daily": round(current_cost - projected_cost, 4),
        "incremental_cost_savings_monthly": round((current_cost - projected_cost) * 30, 2),
        "energy_savings_wh_daily": round(current_wh - projected_wh, 2),
        "energy_savings_pct": round((current_wh - projected_wh) / current_wh * 100, 2) if current_wh else 0.0,
    }


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        opt_cost += pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0
    reasoning = analyze_reasoning_budget(rows)

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")
        print("\n-- Extension 4: Reasoning Budget --")
        print(
            f"reasoning: {reasoning['reasoning_requests']}/{reasoning['total_requests']} requests "
            f"({reasoning['reasoning_traffic_pct']:.2f}% traffic), "
            f"{reasoning['reasoning_cost_pct']:.2f}% cost, "
            f"{reasoning['reasoning_energy_pct']:.2f}% energy"
        )
        print(
            f"cap at {reasoning['target_traffic_pct']:.0f}%: downgrade "
            f"{reasoning['downgraded_requests']} low-complexity requests -> save "
            f"${reasoning['incremental_cost_savings_monthly']:.2f}/month and "
            f"{reasoning['energy_savings_wh_daily']:.0f} Wh/day "
            f"({reasoning['energy_savings_pct']:.1f}% energy)"
        )

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "reasoning_budget": reasoning,
    }


if __name__ == "__main__":
    run()
