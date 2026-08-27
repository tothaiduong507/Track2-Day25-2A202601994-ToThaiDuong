"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(
    baseline_usd: float,
    optimized_usd: float,
    levers: dict,
    sustainability: dict | None = None,
    period: str = "monthly",
    unit_economics: dict | None = None,
    efficiency: dict | None = None,
    extensions: dict | None = None,
    recommendations: list[str] | None = None,
) -> str:
    """Return the complete Markdown deliverable for the FinOps review."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — Báo cáo Tối ưu Chi phí GPU",
        "",
        "## Executive summary",
        "",
        f"**Period:** {period}  ",
        f"**Baseline spend:** ${baseline_usd:,.0f}  ",
        f"**Optimized spend:** ${optimized_usd:,.0f}  ",
        f"**Projected savings:** ${savings:,.0f}  (**{pct:.0f}%**)",
    ]

    if unit_economics:
        lines += [
            "",
            "## Unit economics — USD/1M token",
            "",
            "| Metric | Baseline | Optimized | Improvement |",
            "|---|---:|---:|---:|",
            (
                f"| Inference cost | ${unit_economics['baseline_per_m']:.3f} | "
                f"${unit_economics['optimized_per_m']:.3f} | "
                f"{unit_economics['savings_pct']:.1f}% |"
            ),
            "",
            (
                f"Trên {unit_economics['total_tokens']:,} token/ngày, cascade sang model nhỏ, "
                "prompt caching và batch API làm giảm chi phí đơn vị. Đây là chỉ số nên theo dõi "
                "lâu dài vì nó tách tăng trưởng traffic khỏi hiệu quả phục vụ."
            ),
        ]

    lines += [
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD/month) | Share of savings |",
        "|---|---:|---:|",
    ]
    for name, amount in levers.items():
        share = amount / savings * 100 if savings else 0.0
        lines.append(f"| {name} | ${amount:,.0f} | {share:.1f}% |")

    if efficiency:
        lines += [
            "",
            "## Efficiency audit — GPU-Util lie",
            "",
            "| GPU | Type | GPU-Util | MFU | MBU |",
            "|---|---|---:|---:|---:|",
        ]
        for lie in efficiency.get("lies", []):
            lines.append(
                f"| {lie['gpu_id']} | {lie['gpu_type']} | {lie['gpu_util_pct']:.1f}% | "
                f"{lie['mfu']:.1%} | {lie['mbu']:.1%} |"
            )
        lines += [
            "",
            (
                "`GPU-Util` chỉ cho biết GPU có hoạt động trong khoảng lấy mẫu, không cho biết "
                "bao nhiêu FLOPs hữu ích đã được thực hiện. Memory stall, kernel nhỏ hoặc launch "
                "overhead có thể giữ GPU ở trạng thái bận trong khi MFU vẫn thấp. Vì vậy mua thêm "
                "GPU dựa riêng trên GPU-Util sẽ khuếch đại lãng phí; cần profile kernel, tăng batch "
                "và right-size trước khi mở rộng capacity."
            ),
            "",
            f"Idle telemetry tương đương **${efficiency.get('idle_waste_monthly', 0):,.0f}/tháng**; "
            "đây là phần có thể loại bỏ bằng auto-stop và lịch làm việc.",
        ]

    if sustainability:
        lines += [
            "",
            "## Sustainability",
            "",
            f"- Energy per query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per query: {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Lowest-carbon region: {sustainability.get('best_region', 'n/a')}",
        ]

    if extensions:
        reasoning = extensions.get("reasoning_budget")
        carbon = extensions.get("carbon_aware")
        lines += ["", "## Your Turn extensions"]
        if reasoning:
            lines += [
                "",
                "### Extension 4 — Reasoning Budget",
                "",
                "| Measure | Current | Governed scenario |",
                "|---|---:|---:|",
                f"| Reasoning traffic | {reasoning['reasoning_traffic_pct']:.2f}% | {reasoning['target_traffic_pct']:.0f}% cap |",
                f"| Reasoning requests retained | {reasoning['reasoning_requests']} | {reasoning['retained_reasoning_requests']} |",
                f"| Total inference cost/day | ${reasoning['reasoning_cost_daily'] + reasoning['normal_cost_daily']:.2f} | ${reasoning['projected_cost_daily']:.2f} |",
                f"| Total energy/day | {reasoning['reasoning_energy_wh_daily'] + reasoning['normal_energy_wh_daily']:.0f} Wh | {reasoning['projected_energy_wh_daily']:.0f} Wh |",
                "",
                (
                    f"Reasoning chiếm **{reasoning['reasoning_traffic_pct']:.2f}% traffic** nhưng "
                    f"**{reasoning['reasoning_cost_pct']:.2f}% chi phí** và "
                    f"**{reasoning['reasoning_energy_pct']:.2f}% năng lượng**. Giới hạn reasoning "
                    f"cho 5% request phức tạp nhất (dùng input-token làm proxy) chuyển "
                    f"{reasoning['downgraded_requests']} request/ngày về response thường, tiết kiệm "
                    f"**${reasoning['incremental_cost_savings_monthly']:.2f}/tháng** và "
                    f"**{reasoning['energy_savings_wh_daily']:.0f} Wh/ngày "
                    f"({reasoning['energy_savings_pct']:.1f}%)**. Production nên thay proxy này bằng "
                    "complexity/confidence classifier và theo dõi quality guardrail."
                ),
            ]
        if carbon:
            lines += [
                "",
                "### Extension 5 — Carbon-aware Scheduling",
                "",
                (
                    f"Năm job interruptible dùng {carbon['total_energy_kwh']:.1f} kWh theo công suất "
                    "trung bình quan sát trong telemetry. Chuyển lịch từ "
                    f"`{carbon['current_region']}` sang `{carbon['cleanest_region']}` giảm "
                    f"**{carbon['current_carbon_kg']:.1f} → {carbon['target_carbon_kg']:.1f} kgCO2e "
                    f"({carbon['carbon_savings_pct']:.1f}%)** và chi phí điện "
                    f"**${carbon['current_energy_cost_usd']:.2f} → ${carbon['target_energy_cost_usd']:.2f}**."
                ),
                "",
                "| Region | USD/kWh | gCO2/kWh | Electricity cost | Carbon |",
                "|---|---:|---:|---:|---:|",
            ]
            for row in carbon["region_comparison"]:
                lines.append(
                    f"| {row['region']} | ${row['electricity_usd_per_kwh']:.3f} | "
                    f"{row['carbon_g_per_kwh']} | ${row['energy_cost_usd']:.2f} | "
                    f"{row['carbon_kg']:.2f} kg |"
                )
            lines += [
                "",
                (
                    f"`{carbon['cleanest_region']}` sạch nhất; `{carbon['cheapest_region']}` rẻ nhất. "
                    "Với workload phục vụ người dùng Mỹ, us-east-wa là phương án latency/carbon tốt; "
                    "với training và batch không nhạy latency, europe-north1 tối ưu carbon."
                ),
            ]

    if recommendations:
        lines += ["", "## Prioritized actions"]
        for index, recommendation in enumerate(recommendations, start=1):
            lines.append(f"{index}. {recommendation}")

    lines += [
        "",
        "## Scope and assumptions",
        "",
        "- Core savings use the deterministic one-day inference sample and the monthly purchasing model.",
        f"- Extension scenarios are reported separately and are not double-counted in the {pct:.0f}% core projection.",
        "- Carbon estimates use observed mean GPU power and declared workload duration; networking and facility PUE are excluded.",
        "- Figures are June-2026 snapshots; re-baseline prices, carbon intensity and service quality before acting.",
    ]
    return "\n".join(lines)


def build_writeup(
    baseline_usd: float,
    optimized_usd: float,
    levers: dict,
    unit_economics: dict,
    efficiency: dict,
    extensions: dict,
) -> str:
    """Create the required concise 1–2 page Vietnamese submission write-up."""
    savings = baseline_usd - optimized_usd
    pct = savings / baseline_usd * 100 if baseline_usd else 0.0
    top_lever, top_amount = max(levers.items(), key=lambda item: item[1])
    reasoning = extensions["reasoning_budget"]
    carbon = extensions["carbon_aware"]
    lie_names = ", ".join(lie["gpu_id"] for lie in efficiency["lies"])
    return "\n".join([
        "# Write-up — NimbusAI GPU FinOps",
        "",
        "## 1. Baseline và phương án tối ưu",
        "",
        f"Baseline là **${baseline_usd:,.0f}/tháng** và phương án tối ưu là "
        f"**${optimized_usd:,.0f}/tháng**, tương đương tiết kiệm **${savings:,.0f} "
        f"({pct:.1f}%)**. Riêng inference giảm từ **${unit_economics['baseline_per_m']:.3f}** "
        f"xuống **${unit_economics['optimized_per_m']:.3f}/1M token** "
        f"({unit_economics['savings_pct']:.1f}%) nhờ model cascade, cache và batch.",
        "",
        "## 2. Đóng góp của từng đòn bẩy",
        "",
        "| Đòn bẩy | Tiết kiệm/tháng |",
        "|---|---:|",
        *[f"| {name} | ${amount:,.0f} |" for name, amount in levers.items()],
        "",
        f"Đòn bẩy lớn nhất là **{top_lever}** với **${top_amount:,.0f}/tháng**. "
        "Nó tác động trực tiếp lên số giờ GPU lớn của cả danh mục workload. Inference optimization "
        "có giá trị chiến lược dù số tiền tuyệt đối nhỏ hơn vì nó làm giảm unit cost khi traffic tăng.",
        "",
        "## 3. GPU-Util lie",
        "",
        f"Các GPU bị gắn cờ là **{lie_names}**. Trường hợp nổi bật `gpu-h100-4` có GPU-Util "
        "98,2% nhưng MFU chỉ 19,4%. GPU-Util đo thời gian thiết bị có hoạt động, còn MFU đo FLOPs "
        "hữu ích so với peak. Memory stall, kernel nhỏ hoặc launch overhead có thể làm thiết bị báo bận "
        "mà không tạo throughput tương xứng. Vì vậy cần profile, batching và right-size trước khi mua thêm GPU.",
        "",
        "## 4. Hai phần mở rộng",
        "",
        "### Reasoning Budget",
        "",
        f"Reasoning chiếm {reasoning['reasoning_traffic_pct']:.2f}% request, "
        f"{reasoning['reasoning_cost_pct']:.2f}% chi phí và {reasoning['reasoning_energy_pct']:.2f}% "
        f"năng lượng. Cap ở 5% và chỉ giữ reasoning cho prompt phức tạp nhất tiết kiệm "
        f"**${reasoning['incremental_cost_savings_monthly']:.2f}/tháng** cùng "
        f"**{reasoning['energy_savings_wh_daily']:.0f} Wh/ngày**. Insight: reasoning cần được quản trị "
        "như một ngân sách chất lượng, không nên bật mặc định.",
        "",
        "### Carbon-aware Scheduling",
        "",
        f"Di chuyển 5 job interruptible từ us-east-1 sang europe-north1 giảm phát thải từ "
        f"**{carbon['current_carbon_kg']:.1f} xuống {carbon['target_carbon_kg']:.1f} kgCO2e "
        f"({carbon['carbon_savings_pct']:.1f}%)**. Chi phí điện ước tính cũng giảm từ "
        f"${carbon['current_energy_cost_usd']:.2f} xuống ${carbon['target_energy_cost_usd']:.2f}. "
        "europe-north1 phù hợp cho batch/training; us-east-wa là lựa chọn cân bằng hơn cho người dùng Mỹ.",
        "",
        "## 5. Ba hành động ưu tiên",
        "",
        f"1. Áp dụng spot/reserved theo duty cycle và khả năng checkpoint; đây là lever lớn nhất "
        f"(${top_amount:,.0f}/tháng), nhưng chỉ commit reserved sau khi xác nhận nhu cầu ổn định.",
        "2. Triển khai model cascade, prompt cache và batch API với dashboard USD/1M-token; đây là "
        "quick win ít rủi ro và bảo vệ biên chi phí khi traffic tăng.",
        "3. Bật auto-stop, xử lý GPU-Util lie, đặt reasoning budget và chuyển job interruptible theo "
        "carbon window; theo dõi đồng thời cost, latency, quality và kgCO2e.",
        "",
        "_Các số liệu là snapshot tháng 6/2026 và cần được re-baseline trước khi triển khai thực tế._",
    ])


def savings_waterfall(levers: dict, path: str) -> str:
    """Write a cumulative savings waterfall PNG. No-op if matplotlib is absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = [name.replace(" (", "\n(") for name in levers]
    # ``names`` are display labels; retain original values in insertion order.
    vals = list(levers.values())
    starts = []
    running = 0.0
    for value in vals:
        starts.append(running)
        running += value

    plot_names = names + ["Total\nsavings"]
    plot_vals = vals + [running]
    plot_starts = starts + [0.0]
    colors = ["#2e548a"] * len(vals) + ["#2a9d6f"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(plot_names, plot_vals, bottom=plot_starts, color=colors, width=0.72)
    for i in range(len(vals) - 1):
        level = starts[i] + vals[i]
        ax.plot([i + 0.36, i + 1 - 0.36], [level, level], color="#657080", linewidth=1)
    for bar, value, start in zip(bars, plot_vals, plot_starts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            start + value / 2,
            f"${value:,.0f}",
            ha="center",
            va="center",
            color="white",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_ylabel("Cumulative savings (USD / month)")
    ax.set_title("NimbusAI GPU cost-savings waterfall")
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
