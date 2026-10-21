# CAN Trace — project handoff for a résumé-writing chat

Use the following facts to describe this independent portfolio project. Preserve the qualifications around evaluation. Do not turn a benchmark sample result into a production, cross-vehicle or industry-collaboration claim.

## Project identity

**Name:** CAN Trace — Interpretable CAN Intrusion Forensics with Matrix Product States

**Repository:** https://github.com/Pavan-amikula/can-trace

**Type:** Independent automotive cybersecurity / quantum-inspired machine learning research prototype

**Author / portfolio owner:** Amikula Pavan Kumar Goud

**Status:** Working local implementation, measured public-data evaluation, professional browser interface, recorded demo, test suite and passive receive adapter. Physical vehicle deployment has not been tested.

## Complete project description

CAN Trace investigates how quantum-inspired tensor networks can support interpretable anomaly detection and forensic analysis of in-vehicle Controller Area Network traffic. It learns normal vehicle communication from author-published CAN-MIRGU samples, encodes arbitration identifiers, payload bytes, message sequences and timing into tensor-product features, and scores deviations with actual compressed Matrix Product States. The implementation performs MPS addition, QR orthogonalization, truncated SVD, normalization and explicit tensor contractions on a classical CPU.

The final design conditions normality on the arbitration ID and builds a separate MPS prototype for each observed ID. Each input contains four successive messages of one ID. Every message contributes 11 ID bits, eight payload values, DLC, the preceding global bus gap and the preceding same-ID gap, yielding 88 physical sites. The map is `[cos(0.9x), sin(0.9x)]`. The maximum bond is four. The recorded model has 56 ID prototypes and 152,768 core parameters. At most 48 chronologically spaced training examples are selected per ID, producing 2,576 normal training windows.

The anomaly score is a negative log absolute prototype overlap divided by an ID-specific benign-calibration scale. It is a similarity-based support score, not an attack probability. Unknown IDs have an explicit novelty policy. Timing normalization and alert thresholds use benign data only. Capture partitions are separated before context construction, and labels never enter model features or score computation.

The forensic workspace uses FastAPI server-sent events and a local HTML/CSS/JavaScript interface. It replays a clearly labelled selected public-data excerpt, recomputes scores as windows arrive, and supports pause/resume/reset, playback rates, message selection, signed feature-attribution views, four-message heatmaps, source line offsets, evaluation tables, model diagnostics, and JSON evidence downloads. Explanations measure the score change when a feature is replaced by its normal training median; the conditioning ID stays fixed. Positive deltas mean the feature raises the score relative to that reference. They are model-sensitivity explanations, not additive SHAP values or causal proof.

Evidence exports preserve source/model SHA-256 references, original frame line numbers, model/encoder configuration, scores, thresholds and a hash-linked event record. A verification CLI detects content mutation against a trusted digest. Hashing alone does not authenticate the data source or establish chain of custody.

The project compares the MPS with PCA, per-ID PCA, Isolation Forest and a PyTorch GRU autoencoder using identical normal training windows and representation. It preserves an initial global MPS ablation and its weak results, then documents the rationale for ID conditioning. Controlled software fixtures cover DoS, fuzzing, spoofing, replay and masquerading for functional testing. Only physical injection and a derived masquerade sample have real-dataset evaluation in this version.

## Exact measured evidence

| Fact | Recorded value / interpretation |
|---|---|
| Benign public capture | 368,296 frames |
| Physical injection capture | 508,148 frames; 118 labelled attack frames |
| Derived masquerade capture | 507,995 frames; 118 labelled attack frames |
| Training / calibration / clean test | Chronological 60% / 20% / 20% of benign capture |
| Evaluation windows | Four same-ID messages, stride four per ID; positive if any context frame is attack-labelled |
| Physical injection ranking | AUROC 0.9999, average precision 0.9437 |
| Derived masquerade ranking | AUROC 0.9983, average precision 0.3711 |
| Default threshold recall | 1.0000 on both evaluated attack-window sets |
| Default threshold precision | 0.0085 physical; 0.0044 derived masquerade |
| False alerts / 1,000 normal attack-capture windows | 54.8813 physical; 54.9171 derived masquerade |
| CPU scoring latency | Median 0.65 ms, p95 0.85 ms; excludes parsing, encoding, explanation and network |
| Refit reproducibility | Maximum score difference zero over 256 same-environment probe windows |
| Tests | 15 local tests passed, including mathematical reference, streaming, virtual CAN and API/integrity checks |
| Model archive | ~1.01 MiB packed NPZ, plus JSON configuration inside the archive |

**Necessary interpretation:** The high false-alert burden and low default precision prevent a deployment-readiness claim. Per-ID PCA achieves better AP on these samples; GRU achieves better default F1. The derived masquerade sample is based on the physical capture, so it is not independent evidence. ID conditioning was introduced after examining initial sample results; final results are exploratory and require external validation. The p95 figure is model scoring on one CPU environment, not an end-to-end CAN or ECU guarantee.

## Suggested résumé entry

**CAN Trace — Interpretable CAN Intrusion Detection & Forensics** | Python, NumPy, PyTorch, FastAPI, SocketCAN, Tensor Networks

- Developed an ID-conditioned Matrix Product State anomaly detector for CAN traffic, encoding payload, arbitration-ID, temporal and sequence features into 88-site tensor networks with QR/SVD compression.
- Evaluated normal-only learning against PCA, per-ID PCA, Isolation Forest and a GRU autoencoder on CAN-MIRGU samples; achieved 0.944 physical-injection average precision while documenting false-alert and generalization limitations.
- Built a replay-driven forensic dashboard with byte/timing attribution, source-frame traceability and integrity-verifiable JSON case exports; validated tensor algebra, streaming parity, virtual CAN ingress and APIs with 15 passing tests.
- Measured 0.85 ms p95 CPU model-scoring latency and exact same-environment score agreement across an independent refit; recorded a browser demonstration and reproducible setup/evaluation workflow.

For a short résumé, use three bullets and move latency into the first bullet. Do not say “99.99% accurate,” “state-of-the-art,” “production deployed,” “quantum hardware,” “all attacks detected,” or “ISO compliant.” If space is tight, keep the AP qualification and link the complete evaluation.

## Relevant keywords

Controller Area Network (CAN), automotive cybersecurity, in-vehicle networks, intrusion detection systems (IDS), anomaly detection, CAN bus forensics, arbitration IDs, payload analysis, inter-arrival timing, temporal feature engineering, sequence modelling, normal-only learning, one-class learning, quantum-inspired machine learning, tensor networks, Matrix Product States (MPS), tensor trains, singular value decomposition (SVD), QR factorization, bond dimension, tensor contraction, kernel mean embeddings, interpretable machine learning, explainable AI, feature attribution, model sensitivity, reproducibility, data leakage prevention, class imbalance, precision–recall, average precision, false-positive rate, PCA, Isolation Forest, GRU autoencoder, PyTorch, NumPy, scikit-learn, FastAPI, server-sent events, Python CAN, SocketCAN, software replay, SHA-256, evidence integrity, unit testing, API testing, GitHub Actions.

UNECE R155 and ISO/SAE 21434 belong in a “research context” sentence, not a claimed compliance/implementation credential. CAN-MIRGU is the evaluated dataset. ROAD, CANet/SynCAN and additional datasets were reviewed but not evaluated in this version.

## Why this aligns with the RISE thesis

The project addresses the thesis's central intersection: CAN intrusion detection, tensor-network modelling, interpretable decisions, reproducible experiments and forensic usefulness. It includes the required ID/payload/sequence/timing representation, a real MPS implementation, public-data comparisons with conventional and neural methods, and explicit compactness/latency/reproducibility measurements. The research notes explain attack scenarios, regulatory motivation and deployment recommendations. The project does not claim Swedish industry collaboration or that every proposed research objective has been conclusively solved.

## Interview explanation in approximately one minute

“I built CAN Trace to explore whether tensor networks could make CAN intrusion detection more inspectable. The first global model struggled because different CAN IDs have different payload and timing distributions. I preserved that ablation and moved to an ID-conditioned MPS bank with same-ID temporal context. The model is an explicit sum of product feature states compressed through QR and SVD, and alerts can be traced back to messages, bytes and timing interventions. On the public sample, physical-injection ranking was strong, but the benign-calibrated operating point still generated too many false alerts. I would next validate independently across sessions and vehicles, address timing drift and alert budgets, and evaluate stealthy replay with longer context. The repository includes baselines, tests, evidence exports and a working software-replay demo.”

## Questions to be ready to answer

1. Why use same-ID contexts, and why does CAN ID not identify the transmitting ECU?
2. What does a bond dimension constrain, and how does SVD truncation affect the accumulated normal prototype?
3. Why is a kernel-support score not a probability? Why is the overlap clipped/absolute-valued?
4. Why can high AUROC/AP coexist with low threshold precision under sparse attacks and capture drift?
5. How do capture separation, causal timing features and benign-only scaling prevent common leakage?
6. What information do median-replacement attributions provide, and why are they not causal or additive?
7. What does a source/model hash protect, and what acquisition/custody guarantees remain absent?
8. Why is the derived masquerade capture dependent evidence? What external test would be most useful next?
9. How does stride-1 monitoring differ from stride-4 evaluation? What happens during warm-up or missing-message attacks?
10. Why did per-ID PCA outperform MPS ranking in this small sample, and what would justify using the more complex model?

Before interviewing, run the project, inspect its source and reproduce the results so these statements reflect practical understanding. The supplied job advert has conflicting application/start dates; verify the current dates directly with RISE before applying.
