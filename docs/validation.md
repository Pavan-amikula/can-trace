# Validation record

Recorded locally on 22 October 2026 (Europe/Berlin). The data/model evaluation UTC timestamp and numerical environment are retained in `artifacts/metrics.json`. Observed dependency versions are in `requirements-tested.txt`.

## Executed checks

`python -m pytest -q` — **15 passed** in the final local run. One dependency deprecation warning was emitted by Starlette's httpx test-client compatibility layer; no test failed.

| Area | Verified property |
|---|---|
| MPS algebra | Addition/compression and overlap match a directly expanded small dense tensor to numerical tolerance |
| Rank control | Internal ranks obey the cap and reported discarded squared singular values are nonnegative |
| Serialization | Original and packed conditional model save/load preserve scores |
| Attribution | Reported single-feature score delta matches a direct intervention |
| Entropy | Computed normalized Schmidt entropy respects the tested bond bound |
| Parsing | Original line offsets, varying DLC, malformed payload rejection and timestamp rejection |
| Causality/labels | Appending future frames does not change past features; changing labels does not change features |
| Online parity | Stateful stream features match batch features for chronological and same-ID contexts |
| Scenarios | DoS, fuzzing, spoofing, replay and masquerade fixtures are chronological, labelled and valid classical frames |
| Actual adapter | python-can VirtualBus transmit/receive fixture feeds the passive detector; no hardware involved |
| Integrity | Case payload mutation and chain reordering fail verification |
| Service | Real generated model supports case export, bounds validation, SSE score/attribution agreement and integrity verification |

The generated-model API integration test skips in a fresh CI checkout until evaluation artifacts are regenerated; core mathematical/stream tests run without downloading data. CI is not a substitute for the recorded local full integration run.

## Browser verification

The actual app was exercised through the browser: replay start/pause/reset, speed selection, automatic alert selection, attribution/heatmap/frame display, evaluation tables, model diagnostics and research navigation. The tested browser produced no console errors or warnings. A desktop layout and narrow mobile layout were inspected. Screenshots in `docs/media` are captures of this implementation, not interface mockups.

The MP4 is a ~29-second recording of the real browser replay. UI scores are recomputed from local encoded vectors at arrival. It is deliberately a selected excerpt; the full evaluation is separate. The GIF is a time-sampled preview of that same recording.

## Experiment reproducibility

- Source logs: pinned upstream commit plus expected SHA-256 digests.
- Training: benign capture chronological 60%; calibration 20%; held-out benign 20%. Split first, encode independently.
- Training selection: fixed chronological spacing, up to 48 windows/ID, 2,576 windows total.
- Test: complete physical-injection and derived-masquerade samples, never used as training or threshold-calibration data.
- Development limitation: the ID-conditioned design followed inspection of initial global-model results on these samples. Thus the final sample is not an independent untouched model-selection test.
- Identical-environment independent refit: maximum score difference 0 over 256 calibration probe windows.
- Latency: single-window CPU scoring only, 100 probe measurements, median/p95 reported. The same-ID conditioning, labels, timing transform and explicit novelty rule are documented.

## Remaining unverified claims

No physical vehicle/ECU run, hard real-time deadline, dropped-frame guarantee, full attack-family real-data coverage, independent external generalization, causal explanation, acquisition authentication, regulatory certification or industry collaboration has been established. Numerical ranking performance and the poor default operating point must be reported together.
