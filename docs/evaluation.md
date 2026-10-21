# Measured evaluation

Public CAN-MIRGU samples. Single vehicle / one physical attack and its derived masquerade. No state-of-the-art or production claim.

60/20/20 chronological benign split; capture-local four-message same-ID windows, stride 4 per ID; positive if any context frame labelled attack; thresholds calibrated only on benign traffic

ID-conditioning was introduced after inspecting the global model's sample results. Final sample metrics are exploratory, not an untouched external validation. No attack labels choose thresholds.

| Capture | Model | AUROC | AP | Precision | Recall | F1 | FP / 1k normal |
|---|---|---:|---:|---:|---:|---:|---:|
| held_out_benign | Conditional MPS | — | — | 0.0000 | 0.0000 | 0.0000 | 30.2272 |
| held_out_benign | PCA | — | — | 0.0000 | 0.0000 | 0.0000 | 17.6144 |
| held_out_benign | PCA per-ID | — | — | 0.0000 | 0.0000 | 0.0000 | 96.2270 |
| held_out_benign | Isolation Forest | — | — | 0.0000 | 0.0000 | 0.0000 | 9.8945 |
| held_out_benign | GRU autoencoder | — | — | 0.0000 | 0.0000 | 0.0000 | 18.2668 |
| physical_injection | Conditional MPS | 0.9999 | 0.9437 | 0.0085 | 1.0000 | 0.0169 | 54.8813 |
| physical_injection | PCA | 0.9798 | 0.0122 | 0.0000 | 0.0000 | 0.0000 | 3.7963 |
| physical_injection | PCA per-ID | 1.0000 | 1.0000 | 0.0027 | 1.0000 | 0.0054 | 174.3945 |
| physical_injection | Isolation Forest | 0.6823 | 0.0007 | 0.0000 | 0.0000 | 0.0000 | 3.2686 |
| physical_injection | GRU autoencoder | 0.9973 | 0.0836 | 0.0395 | 1.0000 | 0.0760 | 11.4914 |
| derived_masquerade | Conditional MPS | 0.9983 | 0.3711 | 0.0044 | 1.0000 | 0.0088 | 54.9171 |
| derived_masquerade | PCA | 0.9935 | 0.0279 | 0.0341 | 0.5484 | 0.0642 | 3.7966 |
| derived_masquerade | PCA per-ID | 1.0000 | 1.0000 | 0.0014 | 1.0000 | 0.0028 | 174.4319 |
| derived_masquerade | Isolation Forest | 0.5985 | 0.0003 | 0.0000 | 0.0000 | 0.0000 | 3.2689 |
| derived_masquerade | GRU autoencoder | 0.9961 | 0.0431 | 0.0201 | 0.9677 | 0.0395 | 11.4923 |

MPS and per-ID PCA use separate 99th-percentile benign-calibration thresholds for each ID; scores are divided by those thresholds, then compared strictly to 1. Other baselines use global 99th-percentile thresholds. All use identical training windows and feature representation. AP must be interpreted against low attack prevalence. No test-label threshold tuning.

Scores are window-level; adjacent frames and the derived capture are dependent. No independent-event confidence interval is claimed. The sample does not establish cross-vehicle generalization or reliable replay detection. Rank comparisons across IDs can be affected by per-ID calibration scale.

MPS: 152,768 float64 core parameters; 1,058,427 bytes on disk (compressed NPZ plus metadata). CPU single-window score p95: 0.85 ms, excluding ingestion and explanation.

Independent identical-environment refit max score difference: 0.