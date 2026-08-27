# NimbusAI — Báo cáo Tối ưu Chi phí GPU

## Executive summary

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

## Unit economics — USD/1M token

| Metric | Baseline | Optimized | Improvement |
|---|---:|---:|---:|
| Inference cost | $6.488 | $1.126 | 82.6% |

Trên 7,533,027 token/ngày, cascade sang model nhỏ, prompt caching và batch API làm giảm chi phí đơn vị. Đây là chỉ số nên theo dõi lâu dài vì nó tách tăng trưởng traffic khỏi hiệu quả phục vụ.

## Savings by lever

| Lever | Savings (USD/month) | Share of savings |
|---|---:|---:|
| Inference (cascade/cache/batch) | $1,212 | 9.7% |
| Purchasing (spot/reserved) | $10,040 | 80.3% |
| Right-size util-lies | $655 | 5.2% |
| Kill idle GPUs | $600 | 4.8% |

## Efficiency audit — GPU-Util lie

| GPU | Type | GPU-Util | MFU | MBU |
|---|---|---:|---:|---:|
| gpu-h100-4 | H100 | 98.2% | 19.4% | 20.7% |
| gpu-a10g-1 | A10G | 96.9% | 26.8% | 30.2% |

`GPU-Util` chỉ cho biết GPU có hoạt động trong khoảng lấy mẫu, không cho biết bao nhiêu FLOPs hữu ích đã được thực hiện. Memory stall, kernel nhỏ hoặc launch overhead có thể giữ GPU ở trạng thái bận trong khi MFU vẫn thấp. Vì vậy mua thêm GPU dựa riêng trên GPU-Util sẽ khuếch đại lãng phí; cần profile kernel, tăng batch và right-size trước khi mở rộng capacity.

Idle telemetry tương đương **$600/tháng**; đây là phần có thể loại bỏ bằng auto-stop và lịch làm việc.

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Lowest-carbon region: europe-north1

## Your Turn extensions

### Extension 4 — Reasoning Budget

| Measure | Current | Governed scenario |
|---|---:|---:|
| Reasoning traffic | 8.38% | 5% cap |
| Reasoning requests retained | 201 | 120 |
| Total inference cost/day | $8.48 | $8.03 |
| Total energy/day | 31675 Wh | 21699 Wh |

Reasoning chiếm **8.38% traffic** nhưng **16.46% chi phí** và **94.04% năng lượng**. Giới hạn reasoning cho 5% request phức tạp nhất (dùng input-token làm proxy) chuyển 81 request/ngày về response thường, tiết kiệm **$13.56/tháng** và **9977 Wh/ngày (31.5%)**. Production nên thay proxy này bằng complexity/confidence classifier và theo dõi quality guardrail.

### Extension 5 — Carbon-aware Scheduling

Năm job interruptible dùng 1629.0 kWh theo công suất trung bình quan sát trong telemetry. Chuyển lịch từ `us-east-1` sang `europe-north1` giảm **619.0 → 48.9 kgCO2e (92.1%)** và chi phí điện **$195.48 → $146.61**.

| Region | USD/kWh | gCO2/kWh | Electricity cost | Carbon |
|---|---:|---:|---:|---:|
| us-east-1 | $0.120 | 380 | $195.48 | 619.03 kg |
| us-west-2 | $0.070 | 120 | $114.03 | 195.48 kg |
| europe-north1 | $0.090 | 30 | $146.61 | 48.87 kg |
| europe-central2 | $0.180 | 660 | $293.23 | 1075.16 kg |
| us-east-wa | $0.055 | 90 | $89.60 | 146.61 kg |

`europe-north1` sạch nhất; `us-east-wa` rẻ nhất. Với workload phục vụ người dùng Mỹ, us-east-wa là phương án latency/carbon tốt; với training và batch không nhạy latency, europe-north1 tối ưu carbon.

## Prioritized actions
1. Áp dụng purchasing policy theo duty cycle: spot cho job checkpointable và reserved cho tải ổn định, sau giai đoạn xác nhận nhu cầu. Đây là lever lớn nhất ($10,040/tháng).
2. Triển khai model cascade, prompt cache và batch API; đặt USD/1M-token làm KPI. Chi phí inference giảm 82.6% trong mẫu dữ liệu.
3. Bật auto-stop và profile các GPU-Util lie trước khi mua thêm capacity; đồng thời áp reasoning budget và carbon-aware scheduling với quality/latency guardrail.

## Scope and assumptions

- Core savings use the deterministic one-day inference sample and the monthly purchasing model.
- Extension scenarios are reported separately and are not double-counted in the 46% core projection.
- Carbon estimates use observed mean GPU power and declared workload duration; networking and facility PUE are excluded.
- Figures are June-2026 snapshots; re-baseline prices, carbon intensity and service quality before acting.