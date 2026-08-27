"""M5 — Optimization Report: combine M1-M4 into baseline-vs-optimized (deck §1/§11).

Run: python missions/m5_report.py   ->  outputs/report.md + outputs/savings.png
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import os
from missions._common import num, catalog_by_type, ROOT
from finops import report, sustainability
from missions import m1_efficiency_audit, m2_inference_levers, m3_purchasing

DAYS = 30
# one tier down for over-provisioned ("util-lie") GPUs
RIGHTSIZE_MAP = {"H100": "A100", "H200": "H100", "A100": "A10G", "A10G": "L4", "L4": "L4"}


def run(verbose: bool = True) -> dict:
    r1 = m1_efficiency_audit.run(verbose=False)
    r2 = m2_inference_levers.run(verbose=False)
    r3 = m3_purchasing.run(verbose=False)
    cat = catalog_by_type()

    # --- buckets ---
    infer_savings = (r2["baseline_daily"] - r2["optimized_daily"]) * DAYS
    purchasing_savings = r3["on_demand_monthly"] - r3["optimized_monthly"]

    idle_savings = r1["idle_waste_daily"] * DAYS
    rightsize_savings = 0.0
    for lie in r1["lies"]:
        cur = lie["gpu_type"]
        tgt = RIGHTSIZE_MAP.get(cur, cur)
        delta = num(cat[cur]["on_demand_hr"]) - num(cat[tgt]["on_demand_hr"])
        rightsize_savings += max(0.0, delta) * 24 * DAYS

    levers = {
        "Inference (cascade/cache/batch)": round(infer_savings),
        "Purchasing (spot/reserved)": round(purchasing_savings),
        "Right-size util-lies": round(rightsize_savings),
        "Kill idle GPUs": round(idle_savings),
    }
    baseline = r2["baseline_daily"] * DAYS + r3["on_demand_monthly"]
    optimized = baseline - sum(levers.values())
    total_pct = sum(levers.values()) / baseline * 100 if baseline else 0.0

    # --- sustainability snapshot ---
    median_tokens = 800
    wh = sustainability.wh_per_query(median_tokens)
    sust = {
        "wh_per_query": wh,
        "carbon_g": sustainability.carbon_g(wh, "us-east-1"),
        "best_region": min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get),
    }

    unit_economics = {
        "baseline_per_m": r2["baseline_per_m"],
        "optimized_per_m": r2["optimized_per_m"],
        "savings_pct": r2["savings_pct"],
        "total_tokens": r2["total_tokens"],
    }
    efficiency = {
        "lies": r1["lies"],
        "idle_waste_monthly": idle_savings,
    }
    extensions = {
        "reasoning_budget": r2["reasoning_budget"],
        "carbon_aware": r3["carbon_aware"],
    }
    recommendations = [
        (
            f"Áp dụng purchasing policy theo duty cycle: spot cho job checkpointable và reserved "
            f"cho tải ổn định, sau giai đoạn xác nhận nhu cầu. Đây là lever lớn nhất "
            f"(${purchasing_savings:,.0f}/tháng)."
        ),
        (
            f"Triển khai model cascade, prompt cache và batch API; đặt USD/1M-token làm KPI. "
            f"Chi phí inference giảm {r2['savings_pct']:.1f}% trong mẫu dữ liệu."
        ),
        (
            "Bật auto-stop và profile các GPU-Util lie trước khi mua thêm capacity; đồng thời áp "
            "reasoning budget và carbon-aware scheduling với quality/latency guardrail."
        ),
    ]

    md = report.build_report(
        baseline,
        optimized,
        levers,
        sustainability=sust,
        unit_economics=unit_economics,
        efficiency=efficiency,
        extensions=extensions,
        recommendations=recommendations,
    )
    out_md = os.path.join(ROOT, "outputs", "report.md")
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    writeup = report.build_writeup(
        baseline,
        optimized,
        levers,
        unit_economics,
        efficiency,
        extensions,
    )
    writeup_path = os.path.join(ROOT, "outputs", "writeup.md")
    with open(writeup_path, "w", encoding="utf-8") as f:
        f.write(writeup)
    png = report.savings_waterfall(levers, os.path.join(ROOT, "outputs", "savings.png"))

    if verbose:
        print("== M5 Optimization Report ==")
        print(md)
        print(
            "\nWritten: outputs/report.md + outputs/writeup.md"
            + (" + outputs/savings.png" if png else " (matplotlib absent: PNG skipped)")
        )

    return {"baseline_monthly": round(baseline), "optimized_monthly": round(optimized),
            "levers": levers, "total_savings_pct": round(total_pct, 1),
            "unit_economics": unit_economics, "extensions": extensions,
            "writeup_path": writeup_path}


if __name__ == "__main__":
    run()
