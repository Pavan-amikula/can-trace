# Research and design notes: interpretable CAN intrusion forensics

Research date: 21 October 2026. This document distinguishes published results, inspected dataset facts, and project design choices. The prototype's results must be read from its generated evaluation report; literature performance is not a measurement of this implementation.

## Scope and defensible claims

The research question is whether a compact matrix product state (MPS), trained on normal CAN traffic, provides useful anomaly detection and auditable local explanations at practical CPU inference cost. The immediate deliverable is a reproducible research prototype with replay, investigation views, and evidence export. It does not establish vehicle safety, regulation compliance, causal attack attribution, cross-vehicle generalization, or state-of-the-art performance.

The supplied job advertisement has contradictory dates: November 2026 and November 2024 application deadlines, and a January 2025 start. Treat these as unverified posting errors and ask the named RISE contact for current dates before applying. Do not silently reinterpret them.

## Primary research foundations

| Source | What it establishes | Consequence for this project |
|---|---|---|
| [Oseledets, Tensor-Train Decomposition, SIAM 2011](https://epubs.siam.org/doi/10.1137/090752286) | Low-rank unfolding and sequential SVD enable compact tensor-train representations and efficient operations. | Implement actual rank-3 cores, contractions, rank truncation, and parameter accounting. A flattened PCA model renamed MPS would not meet the objective. |
| [Stoudenmire and Schwab, NeurIPS 2016](https://arxiv.org/abs/1605.05775) | Product feature maps and MPS weights can represent nonlinear learning models; published task is image classification. | The sin/cos local map is a reasonable quantum-inspired starting point, but image results say nothing about CAN detection. |
| [Original TNML repository](https://github.com/emstoudenmire/TNML) | Authors provide proof-of-principle implementations and explicitly caution that training times are not state of the art. | Cite the inspiration. Benchmark the new implementation directly; do not inherit efficiency claims. |
| [Wang et al., Anomaly Detection with Tensor Networks, 2020](https://arxiv.org/abs/2006.02516) | A one-class tensor-network detector learns a regularized matrix product operator, with tabular/image experiments. | This supports the research direction, but the proposed kernel-mean MPS below is a different algorithm and is not a reproduction of TNAD. |
| [Stokes and Terilla, Probabilistic Modeling with MPS, 2019](https://jterilla.github.io/entropy-21-01236-with-cover.pdf) | A gradient-free deterministic sequence of effective updates learns a Born distribution, demonstrated on parity data. | Deterministic training is possible for particular algorithms. MPS as a model family does not automatically imply deterministic optimization or normalized probabilities. |
| [Muandet et al., Kernel Mean Embedding review, 2017](https://arxiv.org/abs/1605.09522) | Distributions can be represented by averages of feature maps, enabling kernel operations on distributions. | Motivates using an empirical normal-traffic feature mean; it is not a proof of this CAN detector's consistency or superiority. |
| [Hanselmann et al., CANet](https://arxiv.org/abs/1906.02492) | Unsupervised CAN intrusion detection considers asynchronous messages of different IDs and frequencies. | Preserve message order and same-ID timing, and include a recurrent reconstruction baseline. A small generic GRU autoencoder is not an exact CANet reproduction. |

## Dataset selection and access

### Immediate real-data evaluation: CAN-MIRGU

The authors' [CAN-MIRGU repository](https://github.com/sampathrajapaksha/CAN-MIRGU) contains a manageable sample. Repository tree and raw endpoints were inspected on the research date. Pin downloads to commit `375ad16faeab5f1cbec145e8a963a3619b1a7207` and record SHA-256 hashes locally. The repository root did not expose a license file in the inspected tree: public download availability must not be described as a permissive redistribution license. Keep raw captures out of the public project and provide a source downloader and citation.

| Capture | Size at inspected revision | Direct source |
|---|---:|---|
| Benign day 1 | 17,158,541 bytes | [Benign_day1_file1.log](https://raw.githubusercontent.com/sampathrajapaksha/CAN-MIRGU/375ad16faeab5f1cbec145e8a963a3619b1a7207/Sample%20dataset/Benign/Day_1/Benign_day1_file1.log) |
| Real brake/fog attack | 23,674,812 bytes | [Break_and_fog_light_attack.log](https://raw.githubusercontent.com/sampathrajapaksha/CAN-MIRGU/375ad16faeab5f1cbec145e8a963a3619b1a7207/Sample%20dataset/Attack/Real_attacks/Break_and_fog_light_attack.log) |
| Derived masquerade | 23,667,468 bytes | [Break_and_fog_light_masquerade_attack.log](https://raw.githubusercontent.com/sampathrajapaksha/CAN-MIRGU/375ad16faeab5f1cbec145e8a963a3619b1a7207/Sample%20dataset/Attack/Masquerade_attacks/Break_and_fog_light_masquerade_attack.log) |
| Derived suspension archive | 5,132,762 bytes | [ID_371_suspension_attack.log.zip](https://raw.githubusercontent.com/sampathrajapaksha/CAN-MIRGU/375ad16faeab5f1cbec145e8a963a3619b1a7207/Sample%20dataset/Attack/Suspension_attacks/ID_371_suspension_attack.log.zip) |

Inspected raw syntax: `(1698232894.363802) can0 153#208010FF00FFB05E 0`. Fields are timestamp in seconds, interface, hexadecimal arbitration ID/payload, binary label. Payload length varies: `164#00080A02` has four bytes; derive DLC instead of assuming eight. Preserve raw line offsets. A CAN-MIRGU label is dataset ground truth and never an input feature.

The [VehicleSec 2024 paper](https://www.ndss-symposium.org/wp-content/uploads/vehiclesec2024-43-paper.pdf) describes 17 hours of benign traffic, 26 real injections and 10 simulated masquerade/suspension captures. Labels are 0/1; suspension labels cover the attack interval because the offending event is a missing frame. The sample brake/fog attack targets ID `07F` with payload pattern `XXC3XXXXXXXXXXXX`; byte index 1 is targeted. Masquerade removes legitimate competing frames after collection. Thus the real and masquerade samples share underlying traffic and are correlated evidence, not independent replication. Full metadata is linked via Google Drive but absent from the inspected sample tree. Sample results cannot establish coverage of every attack family in the full corpus.

### Further datasets

| Dataset | Strength and limitation | Access/licensing decision |
|---|---|---|
| [ROAD, original Zenodo record](https://zenodo.org/records/10462796), [paper](https://arxiv.org/abs/2012.14600) | Real dynamometer captures plus ambient driving; raw candump, targeted fabrication and simulated masquerade; one anonymized vehicle. IDs have been remapped, so their numerical order no longer preserves arbitration priority. Per-message labels require metadata reconstruction. | Official archive is 556.7 MB. Add a manual import workflow and cite the dataset. Do not guess byte semantics or treat all attack-capture frames as malicious. |
| [HCRL Car-Hacking](https://ocslab.hksecurity.net/Datasets/car-hacking-dataset) | Real OBD-II traffic, DoS/fuzzy/gear/RPM spoofing, timestamp/hex ID/DLC/eight byte fields/T-R flag. T is injected, R is normal. | Original page releases for academic experiments and requests citation; Dropbox is the official download. Replay is absent from this particular corpus. Do not infer an open redistribution license. |
| [HCRL dataset catalog](https://ocslab.hksecurity.net/Datasets) | Explicitly distinguishes Car-Hacking from the later Attack & Defense Challenge, which includes replay and a different vehicle. | Keep corpus names precise. Similar file names are not interchangeable datasets. |
| [SynCAN, ETAS](https://github.com/etas/SynCAN), [license](https://github.com/etas/SynCAN/blob/master/License%20terms.txt) | Synthetic signal-space benchmark with continuous, flooding, plateau, playback, suppression and normal tests. Not raw on-vehicle CAN. | Custom terms allow noncommercial research/simulation and prohibit raw or modified dataset distribution and field use. Related work only in this prototype; no data bundled. |
| [can-train-and-test](https://figshare.com/articles/dataset/can-train-and-test/24805533), [paper](https://arxiv.org/abs/2308.04972) | Four vehicles and explicit known/unknown vehicle and attack evaluation partitions. CSV binary frame labels. | CC BY 4.0 is explicit on the original record. Best extension for testing generalization rather than claiming it from one vehicle. Full archive is about 1.4 GB. |

## Proposed model: compressed normal kernel mean

The following is a project design, not a claim from a paper. Scale each continuous feature using normal training data only. For a normalized scalar `x`, use `phi(x) = [cos(pi*x/2), sin(pi*x/2)]`. A window becomes the tensor product `Phi(x)` in a space of dimension `2^d`. Estimate `mu = mean(Phi(x_i))` over normal windows. Represent the sum by MPS cores and compress progressively using SVD with a specified bond cap. A score such as `-log(max(<mu,Phi(x)>, epsilon))` ranks dissimilar windows higher. Explicitly document any absolute value, clipping or normalization applied after approximation.

This score is a compressed similarity estimate. It is not a calibrated attack probability and not a normalized Born density. A sum of product states is a genuine MPS construction, but incremental truncation depends on data order and can bias the estimate. Keep a fixed training order. Verify contractions against an explicit dense tensor for tiny feature dimensions and verify compression error there. Report the bond dimension, core shapes, parameter count, training sample count, and numerical dtype.

Encode arbitration ID, DLC, eight payload bytes, global gap and same-ID gap per frame, then concatenate a causal ordered window. Scalar ID encoding imposes artificial proximity between identifiers; a bitwise or categorical ID ablation is a worthwhile extension. Padding a short payload with zero must be accompanied by DLC, otherwise absent bytes and actual zero bytes are ambiguous. A missing same-ID history needs an explicit convention. Timing transforms should tolerate zero gaps without undefined logs. State whether frame labels are assigned to the final frame or any frame in the window; those answer different questions.

SVD-based training removes stochastic optimizer initialization, but floating point libraries and degenerate singular subspaces can vary by platform. Test repeated predictions and decision agreement on the same pinned environment. Raw core hash equality alone is too strict because MPS gauge/sign changes may preserve the represented function. For the recurrent baseline, follow [PyTorch reproducibility guidance](https://docs.pytorch.org/docs/stable/notes/randomness.html), save seeds and library versions, and avoid cross-platform bitwise guarantees.

## Evaluation protocol

These are proposed experimental safeguards. Use chronological benign training, calibration and test segments with a gap of at least one window between partitions. Keep attack captures entirely outside fitting and threshold selection. Do not randomly split overlapping windows: shared frames make apparent accuracy optimistic. Fit normalization, imputation, model parameters and threshold from their permitted partitions only.

Use a benign calibration quantile for the alert threshold and disclose the target false-positive rate. Show a held-out benign set alongside each attack capture, since capture context alone can induce distribution shift. Compare identical windows/features against Isolation Forest, PCA reconstruction and a modest GRU autoencoder; document differing training budgets. [IsolationForest documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html) explains its random partitions and score convention: invert its normality score before comparing rankings.

Report precision, recall, F1, confusion counts, ROC-AUC and average precision, attack prevalence, sample counts, false positives per time unit, and per-scenario results. Use [scikit-learn's average precision definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html); do not label AP as a trapezoidal PR-AUC without explaining the integration convention. Report threshold-free metrics separately from the fixed-threshold operating point. A few subsampled captures are an exploratory benchmark, not a statistically representative automotive validation.

Measure warm inference latency on the actual machine, distinguish per-window model time from end-to-end UI/serialization cost, and report batch size and number of measurements. Capture-time replay at adjustable speed is useful but is not a hardware real-time guarantee. Separate synthetic attack demos from public-dataset evaluation; never combine synthetic and real metrics into an unlabeled headline.

## Interpretability and forensic limits

Occlude a feature or feature group using normal-training reference values, recompute the anomaly score and record the signed delta. Positive `original - occluded` indicates that feature increased this particular score relative to the chosen reference. Show a frame-by-feature heatmap, byte positions and timing fields, plus raw values and the reference used. Medians across unrelated IDs can create physically implausible payloads; consider per-ID references and baseline sensitivity experiments. Occlusion is model sensitivity, not a causal explanation of compromise, and interacting features mean deltas need not sum to the score.

In canonical MPS form, squared normalized singular values at a bond give a Schmidt spectrum whose entropy summarizes representation complexity across that cut. It depends on encoding and feature order. High bond entropy does not identify an attacked ECU or prove meaningful automotive correlations. Treat it as a structural diagnostic next to validation, not as a byte-level explanation. [NIST's four explainability principles](https://www.nist.gov/publications/four-principles-explainable-artificial-intelligence) motivate understandable evidence, accurate explanations and explicit knowledge limits.

Export the original capture hash, model/configuration hashes, source revision, time range, raw frame offsets, score, threshold, selected alert context, attribution method/reference, and software versions. A hash chain over canonical JSON records can detect local modification when its root is independently trusted. It cannot authenticate a sensor, stop a user recomputing the whole chain, establish who collected evidence, or itself constitute legal chain of custody. [NIST IR 8387](https://nvlpubs.nist.gov/nistpubs/ir/2022/NIST.IR.8387.pdf) recommends separately protected hashes and preserved originals. The [NIST chain-of-custody definition](https://csrc.nist.gov/glossary/term/chain_of_custody) additionally requires a documented handling history. Call the implementation an integrity-verifiable evidence bundle, not tamper-proof forensic proof.

## Regulatory framing

[UNECE R155](https://unece.org/transport/documents/2021/03/standards/un-regulation-no-155-cyber-security-and-cyber-security) covers cybersecurity management and vehicle approval. Its processes include attack monitoring/detection/response and providing information to analyze attempted or successful attacks; see also the [UNECE requirements presentation](https://unece.org/sites/default/files/2023-09/WP5_Session36_KaiFrederikZastrow.pdf). It does not mandate tensor networks, a particular ML explanation method, or a universal intrusion latency. Describe traceability outputs as relevant to investigation workflows, without claiming R155 certification.

[ISO/SAE 21434:2021's official scope](https://www.iso.org/standard/70918.html) addresses lifecycle cybersecurity risk management for road-vehicle electrical/electronic systems and interfaces. It is technology-agnostic. A detector and dashboard alone do not demonstrate compliance with that engineering framework, and the public scope page is not the full standard.

## Professional interface references

Borrow workflow principles, not proprietary assets. [Elastic Security Timeline](https://www.elastic.co/docs/solutions/security/investigate/timeline) connects selected alerts to ordered raw events and drill-down details. Use a persistent alert list with a focused investigation panel showing message context, byte attribution and export. [Grafana dashboard guidance](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/) supports meaningful color, interpretable axes and hierarchical views. Use restrained neutral panels, teal for normal traffic, amber for review and red for threshold breaches; always include text so color is not the sole cue.

A useful page hierarchy is overview (capture/provenance and metrics), replay (controls and anomaly timeline), investigation (selected frame window, payload heatmap, signed occlusion), and benchmark (measured baselines and limitations). Mark recorded replay visibly, show score units and calibration threshold, avoid an invented live-vehicle badge, and keep model diagnostics separate from alert severity.

For subsequent hardware work, [python-can](https://github.com/hardbyte/python-can) supports receive APIs and multiple backends, and [Linux can-utils](https://github.com/linux-can/can-utils) defines the common capture/replay utilities. The initial application can consume logs and later accept receive-only bus frames through the same normalized schema. Hardware input and dropped-frame behavior must be tested before claiming actual vehicle deployment.

## Recommended extension experiments

1. Vary bond cap and window size with normal-only calibration, plotting detection versus parameter count and measured latency.
2. Compare payload-only, timing-only and combined inputs; include categorical or bitwise ID encoding.
3. Evaluate multiple attack families on the full source corpus, then the explicit cross-vehicle partitions of can-train-and-test.
4. Check attribution reference sensitivity and whether masking the documented targeted byte consistently reduces anomaly scores relative to unrelated bytes.
5. Test alert stability under normal driving shift, burst traffic, timestamp precision changes and missing frames.
6. Freeze data hashes and exact commands before final evaluation, then publish every measured baseline, including cases where the MPS loses.
