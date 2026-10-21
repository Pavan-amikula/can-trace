"""Frozen normal-only evaluation protocol; test labels never choose thresholds."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import time

import numpy as np
import sklearn
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_recall_fscore_support,
    confusion_matrix,
)
from threadpoolctl import threadpool_limits

from .baselines import fit_baselines, score as baseline_score
from .data import Encoder, FEATURES, load_frames, sha256
from .tensor import MPSDetector
from .conditional import ConditionalMPS, identifiers

ROOT = Path(__file__).resolve().parents[1]


def metrics(y, s, threshold):
    prediction = s > threshold
    precision, recall, f1, _ = precision_recall_fscore_support(
        y, prediction, average="binary", zero_division=0
    )
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return {
        "windows": len(y),
        "positive_windows": int(y.sum()),
        "prevalence": float(y.mean()),
        "auroc": float(roc_auc_score(y, s)) if len(np.unique(y)) > 1 else None,
        "average_precision": float(average_precision_score(y, s)) if y.sum() else None,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_positives_per_1000_normal": float(fp / max(tn + fp, 1) * 1000),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "threshold": float(threshold),
    }


def batched_score(model, x):
    return np.concatenate(
        [model.score_samples(x[i : i + 4096]) for i in range(0, len(x), 4096)]
    )


def run():
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    print("Loading independent captures", flush=True)
    benign = load_frames(ROOT / "data/raw/benign.log")
    if any(f.label for f in benign):
        raise ValueError("normal-only training capture contains attack labels")
    a, b = int(0.6 * len(benign)), int(0.8 * len(benign))
    train, calibration, clean_test = benign[:a], benign[a:b], benign[b:]
    encoder = Encoder(window=4, context="same_id").fit(train)
    # Windows constructed after the split, so no frames straddle partitions.
    xtrain, _, _ = encoder.transform(train, stride=4)
    xcal, _, _ = encoder.transform(calibration, stride=4)
    model = ConditionalMPS(rank=4, max_per_id=48)
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        print("Fitting ID-conditioned MPS bank / bond 4 / 88 sites", flush=True)
        model.fit(xtrain)
        model.calibrate(xcal)
        train_seconds = time.perf_counter() - started
        model.save(out / "model.npz", encoder.metadata())
        subset = xtrain[sorted(model.training_indices)]
        print(
            f"Training PCA, per-ID PCA, Isolation Forest, GRU on same {len(subset)} windows",
            flush=True,
        )
        baseline_models = fit_baselines(subset)
        thresholds = {
            name: float(np.quantile(baseline_score(m, xcal), 0.99, method="higher"))
            for name, m in baseline_models.items()
        }
        pca_cal = baseline_score(baseline_models["PCA per-ID"], xcal)
        pca_scales = {
            key: max(
                float(
                    np.quantile(
                        pca_cal[identifiers(xcal) == key], 0.99, method="higher"
                    )
                ),
                1e-10,
            )
            for key in model.models
        }
        thresholds["PCA per-ID"] = 1.0
        datasets = {
            "held_out_benign": clean_test,
            "physical_injection": load_frames(ROOT / "data/raw/injection.log"),
            "derived_masquerade": load_frames(ROOT / "data/raw/masquerade.log"),
        }
        result = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": "CAN-MIRGU author-published samples",
            "protocol": "60/20/20 chronological benign split; capture-local four-message same-ID windows, stride 4 per ID; positive if any context frame labelled attack; thresholds calibrated only on benign traffic",
            "development_disclosure": "ID-conditioning was introduced after inspecting the global model's sample results. Final sample metrics are exploratory, not an untouched external validation. No attack labels choose thresholds.",
            "seed": 7,
            "train_frames": len(train),
            "training_windows_used": len(subset),
            "calibration_windows": len(xcal),
            "window": 4,
            "stride": 4,
            "mps": {
                "rank": model.rank,
                "prototypes": model.clusters,
                "sites": len(FEATURES) * 4,
                "parameters": model.parameters,
                "model_bytes": (out / "model.npz").stat().st_size,
                "train_seconds": train_seconds,
                "model_sha256": sha256(out / "model.npz"),
                "bond_entropies_bits": model.bond_entropies(),
            },
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "sklearn": sklearn.__version__,
                "platform": platform.platform(),
                "cpu": platform.processor(),
                "threads": 1,
            },
            "captures": {},
            "results": {},
        }
        for name, frames in datasets.items():
            print(f"Scoring {name}: {len(frames):,} frames", flush=True)
            x, y, ends = encoder.transform(frames, stride=4)
            started = time.perf_counter()
            s = batched_score(model, x)
            elapsed = time.perf_counter() - started
            result["captures"][name] = {
                "frames": len(frames),
                "attack_frames": sum(f.label for f in frames),
                "duration_seconds": frames[-1].timestamp - frames[0].timestamp,
            }
            result["results"][name] = {
                "Conditional MPS": {
                    **metrics(y, s, model.threshold),
                    "score_seconds": elapsed,
                    "windows_per_second": len(x) / elapsed,
                }
            }
            for title, baseline in baseline_models.items():
                t = time.perf_counter()
                bs = baseline_score(baseline, x)
                if title == "PCA per-ID":
                    bid = identifiers(x)
                    bs = np.array(
                        [
                            (
                                value / pca_scales.get(int(key), 1.0)
                                if int(key) in pca_scales
                                else 2.0
                            )
                            for key, value in zip(bid, bs)
                        ]
                    )
                result["results"][name][title] = {
                    **metrics(y, bs, thresholds[title]),
                    "score_seconds": time.perf_counter() - t,
                }
            np.savez_compressed(
                out / f"scores_{name}.npz", labels=y, scores=s, ends=ends
            )
            if name == "physical_injection":
                # Explicitly selected attack-centred segment for a concise demonstration.
                positive = np.flatnonzero(y)
                focus = (
                    int(positive[np.argmax(s[positive])])
                    if len(positive)
                    else int(np.argmax(s))
                )
                lo, hi = max(0, focus - 130), min(len(x), focus + 170)
                events = []
                source_hash = sha256(ROOT / "data/raw/injection.log")
                for idx in range(lo, hi):
                    end = int(ends[idx])
                    key = frames[end].arbitration_id
                    matching = [f for f in frames[: end + 1] if f.arbitration_id == key]
                    window = matching[-4:]
                    events.append(
                        {
                            "index": idx,
                            "timestamp": frames[end].timestamp,
                            "offset_seconds": frames[end].timestamp
                            - frames[int(ends[lo])].timestamp,
                            "score": float(s[idx]),
                            "alert": bool(s[idx] > model.threshold),
                            "ground_truth": int(y[idx]),
                            "frames": [f.record() for f in window],
                            "features": x[idx].tolist(),
                        }
                    )
                replay = {
                    "source": "CAN-MIRGU physical injection sample",
                    "source_sha256": source_hash,
                    "selection": "300-window segment centred on highest-scoring positive window; selected for UI demonstration, not an evaluation sample",
                    "threshold": model.threshold,
                    "events": events,
                }
                (out / "replay.json").write_text(json.dumps(replay))
        # Verify score reproducibility by a completely separate fit, same ordering/settings.
        print("Checking independent MPS refit reproducibility", flush=True)
        repeat = ConditionalMPS(rank=4, max_per_id=48).fit(xtrain)
        repeat.calibrate(xcal)
        probe = xcal[:256]
        result["reproducibility"] = {
            "independent_refit_max_abs_score_difference": float(
                np.max(np.abs(model.score_samples(probe) - repeat.score_samples(probe)))
            ),
            "probe_windows": len(probe),
            "scope": "same environment, data order, settings; cross-platform bit identity not guaranteed",
        }
        latencies = []
        for row in probe[:100]:
            t = time.perf_counter_ns()
            model.score_samples(row[None])
            latencies.append((time.perf_counter_ns() - t) / 1e6)
        result["latency"] = {
            "single_window_p50_ms": float(np.median(latencies)),
            "single_window_p95_ms": float(np.quantile(latencies, 0.95)),
            "includes": "MPS scoring only; excludes parsing, encoding, explanation and network",
        }
    (out / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    write_report(result)
    print("Evaluation written to artifacts/metrics.json", flush=True)
    return result


def write_report(result):
    lines = [
        "# Measured evaluation",
        "",
        "Public CAN-MIRGU samples. Single vehicle / one physical attack and its derived masquerade. No state-of-the-art or production claim.",
        "",
        result["protocol"],
        "",
        result["development_disclosure"],
        "",
        "| Capture | Model | AUROC | AP | Precision | Recall | F1 | FP / 1k normal |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for capture, methods in result["results"].items():
        for name, m in methods.items():
            vals = [
                "—" if m[k] is None else f"{m[k]:.4f}"
                for k in (
                    "auroc",
                    "average_precision",
                    "precision",
                    "recall",
                    "f1",
                    "false_positives_per_1000_normal",
                )
            ]
            lines.append(f"| {capture} | {name} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "MPS and per-ID PCA use separate 99th-percentile benign-calibration thresholds for each ID; scores are divided by those thresholds, then compared strictly to 1. Other baselines use global 99th-percentile thresholds. All use identical training windows and feature representation. AP must be interpreted against low attack prevalence. No test-label threshold tuning.",
        "",
        "Scores are window-level; adjacent frames and the derived capture are dependent. No independent-event confidence interval is claimed. The sample does not establish cross-vehicle generalization or reliable replay detection. Rank comparisons across IDs can be affected by per-ID calibration scale.",
        "",
        f"MPS: {result['mps']['parameters']:,} float64 core parameters; {result['mps']['model_bytes']:,} bytes on disk (compressed NPZ plus metadata). CPU single-window score p95: {result['latency']['single_window_p95_ms']:.2f} ms, excluding ingestion and explanation.",
        "",
        f"Independent identical-environment refit max score difference: {result['reproducibility']['independent_refit_max_abs_score_difference']:.3g}.",
    ]
    (ROOT / "docs/evaluation.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run()
