# So sánh phân phối (Distribution Comparison) Voxtral và Javis

## Nguồn dữ liệu
- Snapshot date: `2026-04-21`
- Voxtral runs: `18-04-2026_v1` đến `19-04-2026_v10` (15 run, thư mục `results/`)
- Javis runs: `19-04-2026_v1` đến `19-04-2026_v10` (10 run, thư mục `results_javis/`)
- Record count: `275` inference record trên `11` file
- Unified snapshot files: [multi_run_records.csv](./data/multi_run_records.csv), [multi_run_summary.json](./data/multi_run_summary.json)

## So sánh tổng thể (Overall Comparison)

| Chỉ số (Metrics) | Voxtral | Javis | Quan sát (Observations) |
| --- | ---: | ---: | --- |
| CER trung bình (11 file) | 45.0% | 34.7% | Javis thấp hơn trên trung bình tổng thể. |
| CER trung bình (9 GT) | 55.0% | 42.4% | Javis vẫn thấp hơn khi bỏ 2 file silence/noise. |
| RTF trung bình | 1.677 | 0.006 | Javis nhanh hơn nhiều bậc. |
| Tỷ lệ ảo giác | 71.5% | 90.0% | Cả hai đều cao theo LLM-eval; Javis cao hơn trên tần suất thực nghiệm. |
| Tỷ lệ nghiêm trọng cao | 30.9% | 36.4% | Javis nhỉnh hơn về tần suất severity high. |

## Xác suất thực nghiệm giữa các run (Empirical Probability between Runs)
- Nếu lấy ngẫu nhiên 1 run Voxtral và 1 run Javis, xác suất Javis có mean CER thấp hơn là 90.0%; 95% CI: 70.0% đến 100.0%.
- Trong cùng phép lấy mẫu đó, xác suất Javis có mean RTF thấp hơn là 100.0%; 95% CI: 100.0% đến 100.0%.

## Xác suất thắng theo từng file (Win Probability by File)

| File | CER trung bình (Mean CER) Voxtral | CER trung bình (Mean CER) Javis | P(Javis CER < Voxtral CER) | 95% CI (Confidence Interval) | Kết luận (Conclusion) |
| --- | ---: | ---: | ---: | --- | --- |
| `media_148394_1767860189485 (1).mp3` | 33.7% | 24.7% | 100.0% | 100.0% đến 100.0% | Javis có lợi thế |
| `media_148414_1767922241264 (1).mp3` | 100.0% | 39.5% | 100.0% | 100.0% đến 100.0% | Javis có lợi thế |
| `media_148280_1767762915627.mp3` | 65.5% | 37.1% | 90.0% | 70.0% đến 100.0% | Javis có lợi thế |
| `media_148954_1768789819598 (1).mp3` | 69.5% | 40.8% | 90.0% | 70.0% đến 100.0% | Javis có lợi thế |
| `media_149733_1769589919400.mp3` | 60.4% | 47.4% | 90.0% | 70.0% đến 100.0% | Javis có lợi thế |
| `media_148439_1767926711644 (1).mp3` | 35.1% | 41.4% | 70.0% | 40.0% đến 100.0% | Javis có lợi thế |
| `media_149291_1769069811005.mp3` | 97.8% | 91.5% | 50.0% | 20.0% đến 80.0% | Hòa |
| `media_148284_1767766514646 (1).mp3` | 15.8% | 26.2% | 0.0% | 0.0% đến 0.0% | Voxtral có lợi thế |
| `media_148393_1767860211615 (1).mp3` | 17.6% | 32.8% | 0.0% | 0.0% đến 0.0% | Voxtral có lợi thế |
| `silence_60s.wav` | 0.0% | 0.0% | 0.0% | 0.0% đến 0.0% | Hòa |
| `stochastic_noise_60s.wav` | 0.0% | 0.0% | 0.0% | 0.0% đến 0.0% | Hòa |

## Quan sát dữ liệu
- Voxtral thắng chắc trên `media_148284_1767766514646 (1).mp3` và `media_148393_1767860211615 (1).mp3`; Javis thắng chắc trên `media_148394_1767860189485 (1).mp3` và `media_148414_1767922241264 (1).mp3`.
- `media_149291_1769069811005.mp3` là file cân bằng nhất về CER giữa hai engine do Javis dao động rất mạnh giữa các run.
- Hai file `silence_60s.wav` và `stochastic_noise_60s.wav` không phân thắng thua về CER vì cả hai đều ghi 0.00% trong snapshot hiện dùng.
