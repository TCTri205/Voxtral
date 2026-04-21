# Báo cáo chỉ số nền (Baseline Metrics Report) - Multi-run

## Nguồn dữ liệu
- Snapshot date: `2026-04-21`
- Voxtral runs: `18-04-2026_v1` đến `19-04-2026_v10` (15 run, thư mục `results/`)
- Javis runs: `19-04-2026_v1` đến `19-04-2026_v10` (10 run, thư mục `results_javis/`)
- Record count: `275` inference record trên `11` file
- Unified snapshot files: [multi_run_records.csv](./data/multi_run_records.csv), [multi_run_summary.json](./data/multi_run_summary.json)

## Phạm vi thống kê (Statistical Scope)
- CER và RTF được tổng hợp trên toàn bộ record; riêng CER trên file hội thoại có GT timestamped được báo riêng cho `9` file.
- Khoảng tin cậy 95% cho mean dùng bootstrap; khoảng tin cậy cho tỷ lệ dùng Wilson interval.

## Thống kê theo engine (Statistics by Engine)

| Engine | CER trung bình (Mean CER) | 95% CI | CER trung bình (9 GT) | 95% CI | Trung vị (Median) CER | Độ lệch chuẩn (Std Dev) CER | Min | Max | P95 | RTF trung bình (Mean RTF) | 95% CI | Tỷ lệ ảo giác (Hallucination Rate) | 95% CI | Tỷ lệ nghiêm trọng cao (High Severity Rate) | 95% CI |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | --- |
| voxtral | 45.0% | 39.8% đến 50.4% | 55.0% | 50.4% đến 60.3% | 35.1% | 34.3% | 0.0% | 100.0% | 100.0% | 1.677 | 1.579 đến 1.776 | 71.5% | 64.2% đến 77.9% | 30.9% | 24.4% đến 38.3% |
| javis | 34.7% | 28.6% đến 41.3% | 42.4% | 36.1% đến 49.7% | 29.0% | 34.1% | 0.0% | 181.7% | 93.9% | 0.006 | 0.005 đến 0.006 | 90.0% | 83.0% đến 94.3% | 36.4% | 28.0% đến 45.7% |

## Độ ổn định theo run (Stability by Run)

| Engine | CER trung bình (Mean CER) giữa các run | Độ lệch chuẩn (Std Dev) CER theo run | RTF trung bình (Mean RTF) giữa các run | Độ lệch chuẩn (Std Dev) RTF theo run | Ghi chú (Notes) |
| --- | ---: | ---: | ---: | ---: | --- |
| voxtral | 45.0% | 0.0% | 1.677 | 0.029 | CER bất biến trên mọi run. |
| javis | 34.7% | 7.1% | 0.006 | 0.000 | CER thay đổi giữa các run. |

## File bất ổn nhất (Least Stable Files) theo CER

| Engine | File | CER trung bình (Mean CER) | Độ lệch chuẩn (Std Dev) CER | Số CER duy nhất (Unique CERs) | Số transcript hash duy nhất (Unique hashes) | Đổi hạng chất lượng (Quality Grade Change) |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| javis | `media_149291_1769069811005.mp3` | 91.5% | 72.4% | 10 | 10 | Có |
| javis | `media_148439_1767926711644 (1).mp3` | 41.4% | 23.9% | 8 | 10 | Có |
| javis | `media_148954_1768789819598 (1).mp3` | 40.8% | 19.8% | 9 | 10 | Có |
| javis | `media_148393_1767860211615 (1).mp3` | 32.8% | 16.3% | 10 | 10 | Có |
| javis | `media_148280_1767762915627.mp3` | 37.1% | 12.7% | 10 | 10 | Có |
| javis | `media_149733_1769589919400.mp3` | 47.4% | 7.5% | 10 | 10 | Có |
| javis | `media_148394_1767860189485 (1).mp3` | 24.7% | 4.1% | 9 | 10 | Có |
| javis | `media_148284_1767766514646 (1).mp3` | 26.2% | 1.9% | 10 | 10 | Không |

## Quan sát dữ liệu
- Voxtral có mean CER toàn bộ snapshot là 45.0%; Javis là 34.7%.
- CER của Voxtral không đổi giữa 15 run, nhưng mean RTF vẫn dao động nhẹ quanh 1.677.
- Javis nhanh hơn hẳn: mean inference RTF 0.006 với p95 0.011.
- Bất ổn CER tập trung ở Javis, nổi bật nhất là `media_149291_1769069811005.mp3` với std CER 72.4%.
