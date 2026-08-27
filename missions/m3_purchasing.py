"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from collections import defaultdict
from missions._common import load_csv, num, catalog_by_type
from finops import pricing, sustainability

DAYS = 30


def analyze_carbon_aware_scheduling(
    jobs: list[dict],
    telemetry: list[dict],
    current_region: str = "us-east-1",
) -> dict:
    """Compare regions for interruptible jobs using observed mean GPU power.

    Only workloads explicitly marked interruptible are movable. Their declared
    duration (hours/day x days x GPU count) is used rather than a blanket monthly
    assumption, so the carbon estimate follows the workload data directly.
    """
    power_samples = defaultdict(list)
    for row in telemetry:
        power_samples[row["gpu_type"]].append(num(row["power_w"]))
    avg_power_w = {
        gpu_type: sum(samples) / len(samples)
        for gpu_type, samples in power_samples.items()
        if samples
    }

    cleanest_region = min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get)
    movable_jobs = []
    total_kwh = 0.0
    for job in jobs:
        if not bool(int(num(job["interruptible"]))):
            continue
        gpu_type = job["gpu_type"]
        gpu_hours = num(job["hours_per_day"]) * num(job["days"]) * int(num(job["num_gpus"]))
        energy_kwh = avg_power_w.get(gpu_type, 0.0) * gpu_hours / 1000.0
        current_carbon_kg = energy_kwh * sustainability.REGION_CARBON[current_region] / 1000.0
        target_carbon_kg = energy_kwh * sustainability.REGION_CARBON[cleanest_region] / 1000.0
        movable_jobs.append({
            "job_id": job["job_id"],
            "gpu_type": gpu_type,
            "gpu_hours": round(gpu_hours, 1),
            "avg_power_w": round(avg_power_w.get(gpu_type, 0.0), 1),
            "energy_kwh": round(energy_kwh, 2),
            "current_carbon_kg": round(current_carbon_kg, 2),
            "target_carbon_kg": round(target_carbon_kg, 2),
            "carbon_savings_kg": round(current_carbon_kg - target_carbon_kg, 2),
        })
        total_kwh += energy_kwh

    region_comparison = []
    for region, intensity in sustainability.REGION_CARBON.items():
        region_comparison.append({
            "region": region,
            "electricity_usd_per_kwh": sustainability.REGION_PRICE_KWH[region],
            "carbon_g_per_kwh": intensity,
            "energy_cost_usd": round(total_kwh * sustainability.REGION_PRICE_KWH[region], 2),
            "carbon_kg": round(total_kwh * intensity / 1000.0, 2),
        })

    current_carbon_kg = total_kwh * sustainability.REGION_CARBON[current_region] / 1000.0
    target_carbon_kg = total_kwh * sustainability.REGION_CARBON[cleanest_region] / 1000.0
    cheapest_region = min(sustainability.REGION_PRICE_KWH, key=sustainability.REGION_PRICE_KWH.get)
    return {
        "current_region": current_region,
        "cleanest_region": cleanest_region,
        "cheapest_region": cheapest_region,
        "movable_jobs": movable_jobs,
        "total_energy_kwh": round(total_kwh, 2),
        "current_carbon_kg": round(current_carbon_kg, 2),
        "target_carbon_kg": round(target_carbon_kg, 2),
        "carbon_savings_kg": round(current_carbon_kg - target_carbon_kg, 2),
        "carbon_savings_pct": round((1 - target_carbon_kg / current_carbon_kg) * 100, 2) if current_carbon_kg else 0.0,
        "current_energy_cost_usd": round(total_kwh * sustainability.REGION_PRICE_KWH[current_region], 2),
        "target_energy_cost_usd": round(total_kwh * sustainability.REGION_PRICE_KWH[cleanest_region], 2),
        "region_comparison": region_comparison,
    }


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    telemetry = load_csv("gpu_telemetry.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0
    carbon_aware = analyze_carbon_aware_scheduling(jobs, telemetry)

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")
        print("\n-- Extension 5: Carbon-aware Scheduling --")
        print(
            f"move {len(carbon_aware['movable_jobs'])} interruptible jobs from "
            f"{carbon_aware['current_region']} to {carbon_aware['cleanest_region']}: "
            f"{carbon_aware['current_carbon_kg']:.1f} -> "
            f"{carbon_aware['target_carbon_kg']:.1f} kgCO2e "
            f"({carbon_aware['carbon_savings_pct']:.1f}% reduction)"
        )
        print(
            f"electricity-only cost: ${carbon_aware['current_energy_cost_usd']:.2f} -> "
            f"${carbon_aware['target_energy_cost_usd']:.2f}; "
            f"cheapest region is {carbon_aware['cheapest_region']}"
        )

    return {"recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
            "carbon_aware": carbon_aware}


if __name__ == "__main__":
    run()
