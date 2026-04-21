# Các trường hợp (Cases) ASR xấu theo ngưỡng cứng (Hard Thresholds) và Tail

## Nguồn dữ liệu
- Snapshot date: `2026-04-21`
- Voxtral runs: `18-04-2026_v1` đến `19-04-2026_v10` (15 run, thư mục `results/`)
- Javis runs: `19-04-2026_v1` đến `19-04-2026_v10` (10 run, thư mục `results_javis/`)
- Record count: `275` inference record trên `11` file
- Unified snapshot files: [multi_run_records.csv](./data/multi_run_records.csv), [multi_run_summary.json](./data/multi_run_summary.json)

## Tiêu chí chọn case xấu (Criteria for Poor Case Selection)
- Ngưỡng cứng: `CER >= 80%`, `RTF >= 2.0`, có `severity=high`, `std CER >= 10`, hoặc đổi hạng chất lượng giữa các run.
- Tail ranking: top 15% theo mean CER, mean RTF, std CER, hoặc high-severity rate trong từng engine.

## Danh sách ưu tiên (Priority List)

| Engine | File | Trigger | CER trung bình (Mean CER) | Độ lệch chuẩn (Std Dev) CER | RTF trung bình (Mean RTF) | Tỷ lệ ảo giác (Hallucination Rate) | Tỷ lệ nghiêm trọng cao (High Severity Rate) | Số transcript hash duy nhất (Unique hashes) | Audio rolloff (Hz) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| javis | `media_149291_1769069811005.mp3` | CER>=80%, Có severity=high, CER std>=10, Đổi hạng chất lượng giữa các run, Top tail CER, Top tail bất ổn | 91.5% | 72.4% | 0.002 | 90.0% | 40.0% | 10 | 1891 |
| voxtral | `media_148414_1767922241264 (1).mp3` | CER>=80%, Có severity=high, Top tail CER, Top tail severity high | 100.0% | 0.0% | 1.825 | 93.3% | 93.3% | 1 | 2364 |
| javis | `media_149733_1769589919400.mp3` | Có severity=high, Đổi hạng chất lượng giữa các run, Top tail CER, Top tail severity high | 47.4% | 7.5% | 0.003 | 100.0% | 90.0% | 10 | 2050 |
| javis | `media_148439_1767926711644 (1).mp3` | Có severity=high, CER std>=10, Đổi hạng chất lượng giữa các run, Top tail bất ổn | 41.4% | 23.9% | 0.009 | 100.0% | 60.0% | 10 | 2141 |
| voxtral | `media_148439_1767926711644 (1).mp3` | RTF>=2.0, Có severity=high, Top tail severity high, Top tail RTF | 35.1% | 0.0% | 2.426 | 93.3% | 93.3% | 1 | 2141 |
| javis | `media_148393_1767860211615 (1).mp3` | Có severity=high, CER std>=10, Đổi hạng chất lượng giữa các run, Top tail RTF | 32.8% | 16.3% | 0.010 | 100.0% | 30.0% | 10 | 2554 |
| javis | `media_148954_1768789819598 (1).mp3` | Có severity=high, CER std>=10, Đổi hạng chất lượng giữa các run | 40.8% | 19.8% | 0.003 | 100.0% | 60.0% | 10 | 2272 |
| javis | `media_148280_1767762915627.mp3` | Có severity=high, CER std>=10, Đổi hạng chất lượng giữa các run | 37.1% | 12.7% | 0.004 | 100.0% | 20.0% | 10 | 1937 |
| voxtral | `media_149291_1769069811005.mp3` | CER>=80%, Top tail CER | 97.8% | 0.0% | 0.611 | 0.0% | 0.0% | 1 | 1891 |
| voxtral | `media_148394_1767860189485 (1).mp3` | RTF>=2.0, Top tail RTF | 33.7% | 0.0% | 2.453 | 93.3% | 0.0% | 1 | 2402 |
| javis | `media_148394_1767860189485 (1).mp3` | Đổi hạng chất lượng giữa các run, Top tail RTF | 24.7% | 4.1% | 0.009 | 100.0% | 0.0% | 10 | 2402 |
| voxtral | `media_149733_1769589919400.mp3` | Có severity=high | 60.4% | 0.0% | 0.891 | 80.0% | 80.0% | 1 | 2050 |

## Quan sát dữ liệu

- `voxtral / media_148414_1767922241264 (1).mp3` nổi bật vì CER>=80%, Có severity=high, Top tail CER; mean CER 100.0%, std CER 0.0%, rolloff 2364 Hz.
- `voxtral / media_148439_1767926711644 (1).mp3` nổi bật vì RTF>=2.0, Có severity=high, Top tail severity high; mean CER 35.1%, std CER 0.0%, rolloff 2141 Hz.
- `voxtral / media_149291_1769069811005.mp3` nổi bật vì CER>=80%, Top tail CER; mean CER 97.8%, std CER 0.0%, rolloff 1891 Hz.
- `voxtral / media_148394_1767860189485 (1).mp3` nổi bật vì RTF>=2.0, Top tail RTF; mean CER 33.7%, std CER 0.0%, rolloff 2402 Hz.
- `javis / media_149291_1769069811005.mp3` nổi bật vì CER>=80%, Có severity=high, CER std>=10; mean CER 91.5%, std CER 72.4%, rolloff 1891 Hz.
- `javis / media_149733_1769589919400.mp3` nổi bật vì Có severity=high, Đổi hạng chất lượng giữa các run, Top tail CER; mean CER 47.4%, std CER 7.5%, rolloff 2050 Hz.
- `javis / media_148439_1767926711644 (1).mp3` nổi bật vì Có severity=high, CER std>=10, Đổi hạng chất lượng giữa các run; mean CER 41.4%, std CER 23.9%, rolloff 2141 Hz.
- `javis / media_148393_1767860211615 (1).mp3` nổi bật vì Có severity=high, CER std>=10, Đổi hạng chất lượng giữa các run; mean CER 32.8%, std CER 16.3%, rolloff 2554 Hz.

## Giả thuyết kỹ thuật (Technical Hypotheses)
- Các file có rolloff quanh 1.9 kHz đến 2.4 kHz nhiều khả năng thuộc narrowband telephony; đây là một tương quan quan sát được, không phải bằng chứng nhân quả đầy đủ.
- Ở Javis, số lượng transcript hash khác nhau cao trên cùng một file gợi ý thành phần decoder hoặc streaming path có biến thiên giữa các run.
- Ở Voxtral, các case xấu không đến từ dao động run-to-run mà đến từ một lỗi có tính lặp lại trên cùng loại đầu vào.
