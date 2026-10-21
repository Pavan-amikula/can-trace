# Architecture and experimental contract

## Acquisition and representation

The parser accepts classical 11-bit candump/MIRGU logs, or canonical CSV with `timestamp,can_id,data,label`. IDs and data are hexadecimal; label is optional binary ground truth. It rejects malformed payloads, decreasing timestamps, extended IDs and mixed channels. Equal timestamps are permitted. Input is not silently sorted. Original log line numbers remain in frame records.

Features are computed causally in acquisition order. Identifier bits are binary, bytes are divided by 255, DLC by 8, and timing is mapped by `1-exp(-gap/(3*training_median_positive_gap))`. The two medians use normal training only. Short payloads are zero padded and carry DLC; absent bytes have no separate mask. Cold-start bus/same-ID gaps are zero. Ground truth never enters feature extraction or scoring.

Four successive messages of one ID form a context. Gaps are measured in the complete bus stream before grouping, so global bus timing is retained. Training/calibration/test splits are made before encoding; group histories never cross partitions. Windows are evaluated with stride 4 per ID, so no frame is reused by that ID's evaluation windows. Message order within each context is preserved. A positive window contains at least one labelled attack frame; metrics are window-level, not 118-frame attack recall.

The stream path maintains per-ID histories and emits after four messages of an ID, then every message (stride 1). It rejects backwards time and changing channels. It has bounded message-context buffers and at most 2,048 ID states. It cannot score a missing message without a separate timer. No frame is transmitted by the monitor.

## MPS training and scoring

Each feature has a two-dimensional sin/cos map. A product state has rank-one cores. Addition makes block-diagonal internal cores; left QR orthogonalization followed by right-to-left SVD truncates the bond dimension. The sum is order-dependent under truncation. Training fixes chronological selection, order, rank 4, angle 0.9 and 48 examples/ID maximum. L2 normalization makes prototype overlap comparable within an ID.

This is a compressed empirical kernel mean, not generative density training, DMRG, TNAD, or Born normalization. Scoring takes the absolute overlap because truncation can introduce sign effects; it clips at `[1e-15,1]` before negative log. The calibration scale is the matching ID's normal 99th percentile with a floor `1e-8`. The default alert threshold is the ratio 1. Unknown IDs receive ratio 2 by a documented explicit policy, after the four-message warm-up.

Extremely small calibration denominators and capture drift can increase false alerts. The high default false-alert rates are a central finding, not hidden by a favourable test-selected threshold. Threshold/feature design was iterated on these samples, so results are exploratory. External untouched testing remains necessary.

Model archives use NumPy arrays and JSON with `allow_pickle=False`; packed weights and explicit core shapes avoid thousands of small ZIP entries. Same-environment refits are checked by predictions, since MPS gauge changes can change cores without changing the represented function. No cross-machine bitwise guarantee is made.

## Baselines and fairness

Every model fits the identical 2,576 normal training windows and sees the identical 88-dimensional representation. Global PCA uses 12 components, Isolation Forest 100 trees, and the GRU autoencoder a 24-unit encoder with a small dense reconstruction decoder trained for 30 epochs. Per-ID PCA uses up to 8 components, and is an explicitly strong conditional baseline.

MPS/per-ID PCA have separate per-ID benign calibration scales. Global models use a global 99th-percentile benign threshold. This is a transparent architectural difference, not a matched compute-budget or exhaustive hyperparameter study. The GRU is not CANet, and none of these baselines represents an exhaustive state-of-the-art comparison. The original global MPS result uses chronological mixed-ID windows and a different training budget; it is a design ablation, not a controlled one-variable comparison.

## Service and UI

FastAPI binds to `127.0.0.1`. A fixed selected local replay artifact drives SSE. Scores are recomputed from its already encoded vectors as events are emitted; parsing/encoding were performed during evaluation. Live passive monitoring separately exercises stateful online encoding. Pausing closes the stream and resuming uses a cursor. The UI identifies the source and its deliberately selected attack-centred excerpt; it never substitutes excerpt counts for full-capture results.

The API reads only configured local artifacts. It has no arbitrary filesystem path endpoint, model upload, outgoing analytics or vehicle control. HTTP headers prevent framing/content sniffing and restrict scripts/styles to local assets. There is no authentication or multi-user isolation, so the default service is a localhost research tool.

| Endpoint | Behaviour |
|---|---|
| `/api/health` | Setup/ready state |
| `/api/summary` | Source/model hashes, settings, recorded evaluation |
| `/api/stream?start=0&speed=20` | SSE replay with fresh tensor scores; 1–50 windows/s |
| `/api/case/{position}` | Frame evidence and fresh attribution |
| `/api/case/{position}/export` | Download content-addressed JSON |
| `/openapi.json` | Machine-readable API schema |

## Forensic case semantics

Canonical JSON sorts keys, removes insignificant separators and rejects NaN. Each event hashes its content plus the previous event hash. A case hashes its configuration, source/model digests and event chain. The source digest refers to the complete original log. The model digest refers to the exact saved archive used locally. Original line numbers locate the frame in that source.

The public synthetic case demonstrates the schema without redistributing a real capture. Exported real cases are local artifacts. A trusted retained digest can detect changes; an adversary can replace both an unsigned case and its digest. Signing, secure acquisition, trusted timestamps, access control and custody records remain future work.

## Requirement coverage and remaining evidence

| Thesis requirement | Implemented evidence | Remaining research |
|---|---|---|
| Literature review | Primary-source research notes and citations | Systematic review and university supervision |
| CAN attack scenarios | Real physical/derived-masquerade samples; five synthetic fixture families | Independent real DoS/fuzz/replay datasets and full corpus |
| IDs, payloads, sequences, timing | Causal 88-site same-ID context | DBC semantics, CAN FD, longer-range context |
| Tensor-network anomaly detection | Actual MPS core addition, contractions, QR/SVD | Larger data budgets, bond/order studies, alternative TN architectures |
| Interpretability | Feature intervention deltas and bond entropies | Expert validation and explanation-fidelity evaluation |
| ML/deep-learning comparison | PCA, per-ID PCA, IF and GRU | Published architecture reproductions and fair tuning budgets |
| Compactness/reproducibility | Parameter/file accounting and independent refit | Cross-platform/ECU profiling and all-baseline size study |
| Forensics | Source offsets, configuration and integrity-linked cases | Authenticated acquisition and legal evidentiary process |
| Deployment recommendations | Explicit limitations and research roadmap | Vehicle partner validation; no industry collaboration claimed |
