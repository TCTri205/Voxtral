# Hallucination analysis (Phân tích ảo giác) - Multi-run

## Nguồn dữ liệu
- Snapshot date: `2026-04-21`
- Voxtral runs: `18-04-2026_v1` đến `19-04-2026_v10` (15 run, thư mục `results/`)
- Javis runs: `19-04-2026_v1` đến `19-04-2026_v10` (10 run, thư mục `results_javis/`)
- Record count: `275` inference record trên `11` file
- Unified snapshot files: [multi_run_records.csv](./data/multi_run_records.csv), [multi_run_summary.json](./data/multi_run_summary.json)

## Tần suất thực nghiệm theo engine (Empirical Frequency by Engine)

| Engine | Tỷ lệ ảo giác (Hallucination Rate) | 95% CI | Tỷ lệ nghiêm trọng cao (High Severity Rate) | 95% CI | Loại lỗi chính (Primary Error Type) |
| --- | ---: | --- | ---: | --- | --- |
| voxtral | 71.5% | 64.2% đến 77.9% | 30.9% | 24.4% đến 38.3% | `insertion` |
| javis | 90.0% | 83.0% đến 94.3% | 36.4% | 28.0% đến 45.7% | `insertion` |

## Phân bổ mức độ (Severity Distribution)

| Engine | none | low | medium | high |
| --- | ---: | ---: | ---: | ---: |
| voxtral | 43 | 6 | 61 | 51 |
| javis | 11 | 0 | 59 | 40 |

## File có rủi ro nghiêm trọng cao nhất (Files with Highest High Severity Risk)

| Engine | File | Tỷ lệ nghiêm trọng cao (High Severity Rate) | Tỷ lệ ảo giác (Hallucination Rate) | Loại lỗi hỗn hợp chính (Primary Mixed Error Types) |
| --- | --- | ---: | ---: | --- |
| voxtral | `media_148439_1767926711644 (1).mp3` | 93.3% | 93.3% | insertion:14, none:1; hash=1 |
| voxtral | `media_148414_1767922241264 (1).mp3` | 93.3% | 93.3% | silence_text:9, content_replacement:3, insertion:2, none:1; hash=1 |
| javis | `media_149733_1769589919400.mp3` | 90.0% | 100.0% | insertion:10; hash=10 |
| voxtral | `media_149733_1769589919400.mp3` | 80.0% | 80.0% | content_replacement:8, insertion:4, none:3; hash=1 |
| javis | `media_148954_1768789819598 (1).mp3` | 60.0% | 100.0% | insertion:10; hash=10 |
| javis | `media_148439_1767926711644 (1).mp3` | 60.0% | 100.0% | insertion:9, content_replacement:1; hash=10 |
| javis | `media_149291_1769069811005.mp3` | 40.0% | 90.0% | insertion:9, none:1; hash=10 |
| javis | `media_148393_1767860211615 (1).mp3` | 30.0% | 100.0% | insertion:9, content_replacement:1; hash=10 |
| javis | `media_148280_1767762915627.mp3` | 20.0% | 100.0% | insertion:10; hash=10 |

## Silence/noise evaluator artifacts

| Engine | File | Tỷ lệ nghiêm trọng cao (High Severity Rate) | Tỷ lệ ảo giác (Hallucination Rate) | Loại lỗi hỗn hợp chính (Primary Mixed Error Types) | Ghi chú |
| --- | --- | ---: | ---: | --- | --- |
| javis | `silence_60s.wav` | 100.0% | 100.0% | silence_text:10; hash=1 | Không đưa vào bảng chính vì CER của file này bằng 0.00%. |
| voxtral | `silence_60s.wav` | 73.3% | 73.3% | silence_text:11, none:2, unknown:2; hash=1 | Không đưa vào bảng chính vì CER của file này bằng 0.00%. |
| voxtral | `stochastic_noise_60s.wav` | 0.0% | 0.0% | none:13, unknown:2; hash=1 | Không đưa vào bảng chính vì CER của file này bằng 0.00%. |
| javis | `stochastic_noise_60s.wav` | 0.0% | 0.0% | none:10; hash=1 | Không đưa vào bảng chính vì CER của file này bằng 0.00%. |

## Quan sát dữ liệu
- Javis có hallucination rate cao hơn Voxtral trên snapshot này, nhưng phần lớn dưới dạng insertion/content replacement thay vì một mode lỗi duy nhất.
- `silence_60s.wav` và `stochastic_noise_60s.wav` được tách riêng thành nhóm artifact của evaluator, vì chúng không đại diện cho lỗi nhận dạng hội thoại thông thường.
- `silence_60s.wav` bị gắn `silence_text` lặp lại ở cả hai engine trong nhiều run, vì vậy cần coi đây là tín hiệu của lớp evaluator chứ không phải bằng chứng tuyệt đối về đầu ra sai.
- Vì lý do đó, các file silence/noise với CER = 0.00% không được đưa vào bảng high-severity chính.
- Với Voxtral, transcript hash theo file là bất biến giữa các run nhưng nhãn LLM-eval vẫn dao động ở một số file; điều này cho thấy tầng đánh giá có độ nhiễu riêng.

## Giả thuyết kỹ thuật (Technical Hypotheses)
- Khi hypothesis giữ nguyên mà nhãn severity thay đổi, biến thiên nhiều khả năng đến từ LLM evaluator hoặc prompt framing, không đến từ ASR engine.
- Các file narrowband có xu hướng xuất hiện insertion nhiều hơn, phù hợp với giả thuyết decoder cố lấp khoảng trống bằng chuỗi quen thuộc.
