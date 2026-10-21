# Measured evaluation

Public CAN-MIRGU samples. Single vehicle / one physical attack and its derived masquerade. No state-of-the-art or production claim.

60/20/20 chronological benign split; capture-local nonoverlapping 4-frame windows; attack captures never train/calibrate; positive if any frame labelled attack

| Capture | Model | AUROC | AP | Precision | Recall | F1 | FP / 1k normal |
|---|---|---:|---:|---:|---:|---:|---:|
| held_out_benign | MPS kernel mean | — | — | 0.0000 | 0.0000 | 0.0000 | 1.6291 |
| held_out_benign | PCA | — | — | 0.0000 | 0.0000 | 0.0000 | 6.5164 |
| held_out_benign | Isolation Forest | — | — | 0.0000 | 0.0000 | 0.0000 | 6.0820 |
| held_out_benign | GRU autoencoder | — | — | 0.0000 | 0.0000 | 0.0000 | 7.0052 |
| physical_injection | MPS kernel mean | 0.7764 | 0.0031 | 0.0050 | 0.0254 | 0.0084 | 4.6644 |
| physical_injection | PCA | 0.8244 | 0.0069 | 0.0130 | 0.0847 | 0.0225 | 5.9960 |
| physical_injection | Isolation Forest | 0.6586 | 0.0019 | 0.0029 | 0.0169 | 0.0050 | 5.3262 |
| physical_injection | GRU autoencoder | 0.8541 | 0.0060 | 0.0074 | 0.0678 | 0.0134 | 8.4227 |
| derived_masquerade | MPS kernel mean | 0.7795 | 0.0045 | 0.0145 | 0.0763 | 0.0244 | 4.8235 |
| derived_masquerade | PCA | 0.8437 | 0.0144 | 0.0243 | 0.1610 | 0.0422 | 6.0214 |
| derived_masquerade | Isolation Forest | 0.7410 | 0.0032 | 0.0016 | 0.0085 | 0.0026 | 5.0363 |
| derived_masquerade | GRU autoencoder | 0.8630 | 0.0170 | 0.0137 | 0.1271 | 0.0248 | 8.5041 |

Thresholds are independent 99th-percentile benign-calibration scores. Predictions use strict score > threshold. AP must be interpreted against the very low attack prevalence. No test-label threshold tuning.

Scores are window-level; adjacent frames and the derived capture are dependent. No independent-event confidence interval is claimed. The sample does not establish cross-vehicle generalization or reliable replay detection.

MPS: 63,984 float64 core parameters; 619,479 bytes on disk (compressed NPZ plus metadata). CPU single-window score p95: 51.58 ms, excluding ingestion and explanation.

Independent identical-environment refit max score difference: 0.