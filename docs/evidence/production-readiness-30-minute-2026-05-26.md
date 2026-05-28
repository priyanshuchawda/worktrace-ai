# 30-Minute Production Readiness Benchmark

This is a 30-minute local recorder pipeline benchmark. It measures capture/resource behavior only; cloud inference and model quality benchmarks are separate.

Scope: local recorder pipeline only. Cloud inference, Gemini/Gemma development-provider calls, OCR/VLM/audio model benchmarks, and report-quality scoring are excluded and must be measured separately.

Safety: this report contains aggregate metrics only; raw active-window titles are not included, screenshot pixels are not included, temporary screenshots are deleted by default, and no raw artifacts are committed.

- Benchmark profile: `production-30-minute`
- Session ID: `sess_laptop_readiness_2159e22468f4`
- Started: `2026-05-26T17:53:32.047072+05:30`
- Finished: `2026-05-26T18:23:35.872956+05:30`
- Requested duration: `1800.000` seconds
- Sample interval: `10.000` seconds
- Raw event count: `175`
- Screenshot count: `94`
- Cloud request count: `0`
- Privacy violation count: `0`
- Temporary workspace cleaned: `yes`

## Resource Budget

| metric | actual | budget | passed |
| --- | ---: | ---: | --- |
| duration_minutes | 30.17 | 30.00 | yes |
| average_cpu_percent | 2.96 | 15.00 | yes |
| peak_ram_mb | 40.80 | 800.00 | yes |
| db_growth_mb | 0.18 | 100.00 | yes |
| screenshot_mb_per_hour | 15.46 | 250.00 | yes |
| model_loaded_during_recording | 0.00 | 0.00 | yes |

## Violations

- none
