# Write-up — NimbusAI GPU FinOps

## 1. Baseline và phương án tối ưu

Baseline là **$27,133/tháng** và phương án tối ưu là **$14,626/tháng**, tương đương tiết kiệm **$12,507 (46.1%)**. Riêng inference giảm từ **$6.488** xuống **$1.126/1M token** (82.6%) nhờ model cascade, cache và batch.

## 2. Đóng góp của từng đòn bẩy

| Đòn bẩy | Tiết kiệm/tháng |
|---|---:|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

Đòn bẩy lớn nhất là **Purchasing (spot/reserved)** với **$10,040/tháng**. Nó tác động trực tiếp lên số giờ GPU lớn của cả danh mục workload. Inference optimization có giá trị chiến lược dù số tiền tuyệt đối nhỏ hơn vì nó làm giảm unit cost khi traffic tăng.

## 3. GPU-Util lie

Các GPU bị gắn cờ là **gpu-h100-4, gpu-a10g-1**. Trường hợp nổi bật `gpu-h100-4` có GPU-Util 98,2% nhưng MFU chỉ 19,4%. GPU-Util đo thời gian thiết bị có hoạt động, còn MFU đo FLOPs hữu ích so với peak. Memory stall, kernel nhỏ hoặc launch overhead có thể làm thiết bị báo bận mà không tạo throughput tương xứng. Vì vậy cần profile, batching và right-size trước khi mua thêm GPU.

## 4. Hai phần mở rộng

### Reasoning Budget

Reasoning chiếm 8.38% request, 16.46% chi phí và 94.04% năng lượng. Cap ở 5% và chỉ giữ reasoning cho prompt phức tạp nhất tiết kiệm **$13.56/tháng** cùng **9977 Wh/ngày**. Insight: reasoning cần được quản trị như một ngân sách chất lượng, không nên bật mặc định.

### Carbon-aware Scheduling

Di chuyển 5 job interruptible từ us-east-1 sang europe-north1 giảm phát thải từ **619.0 xuống 48.9 kgCO2e (92.1%)**. Chi phí điện ước tính cũng giảm từ $195.48 xuống $146.61. europe-north1 phù hợp cho batch/training; us-east-wa là lựa chọn cân bằng hơn cho người dùng Mỹ.

## 5. Ba hành động ưu tiên

1. Áp dụng spot/reserved theo duty cycle và khả năng checkpoint; đây là lever lớn nhất ($10,040/tháng), nhưng chỉ commit reserved sau khi xác nhận nhu cầu ổn định.
2. Triển khai model cascade, prompt cache và batch API với dashboard USD/1M-token; đây là quick win ít rủi ro và bảo vệ biên chi phí khi traffic tăng.
3. Bật auto-stop, xử lý GPU-Util lie, đặt reasoning budget và chuyển job interruptible theo carbon window; theo dõi đồng thời cost, latency, quality và kgCO2e.

_Các số liệu là snapshot tháng 6/2026 và cần được re-baseline trước khi triển khai thực tế._