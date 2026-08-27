import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from missions._common import load_csv
from missions.m2_inference_levers import analyze_reasoning_budget
from missions.m3_purchasing import analyze_carbon_aware_scheduling


def test_reasoning_budget_cap_saves_cost_and_energy():
    result = analyze_reasoning_budget(load_csv("token_usage.csv"), target_share=0.05)

    assert result["reasoning_traffic_pct"] > result["target_traffic_pct"]
    assert result["downgraded_requests"] > 0
    assert result["incremental_cost_savings_monthly"] > 0
    assert result["energy_savings_wh_daily"] > 0
    assert result["reasoning_energy_pct"] > result["reasoning_traffic_pct"]


def test_carbon_aware_scheduling_compares_all_regions():
    result = analyze_carbon_aware_scheduling(
        load_csv("workloads.csv"),
        load_csv("gpu_telemetry.csv"),
    )

    assert result["cleanest_region"] == "europe-north1"
    assert result["cheapest_region"] == "us-east-wa"
    assert len(result["movable_jobs"]) == 5
    assert len(result["region_comparison"]) == 5
    assert result["carbon_savings_kg"] > 0
    assert result["target_carbon_kg"] < result["current_carbon_kg"]
