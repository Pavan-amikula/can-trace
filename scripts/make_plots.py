"""Regenerate the published scientific figure from measured score artifacts."""

from pathlib import Path
import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve

ROOT = Path(__file__).resolve().parents[1]


def main():
    metrics = json.loads((ROOT / "artifacts/metrics.json").read_text())
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, axes = plt.subplots(
        1, 2, figsize=(12, 4.5), gridspec_kw={"width_ratios": [1.25, 1]}
    )
    for name, title, color in [
        ("physical_injection", "Physical injection", "#0c8274"),
        ("derived_masquerade", "Derived masquerade", "#be7838"),
    ]:
        with np.load(ROOT / f"artifacts/scores_{name}.npz") as data:
            precision, recall, _ = precision_recall_curve(
                data["labels"], data["scores"]
            )
        ap = metrics["results"][name]["Conditional MPS"]["average_precision"]
        axes[0].step(
            recall, precision, where="post", color=color, label=f"{title} · AP {ap:.3f}"
        )
    axes[0].set(
        xlabel="Recall",
        ylabel="Precision",
        xlim=(0, 1.01),
        ylim=(0, 1.04),
        title="Ranking quality on sparse labelled attacks",
    )
    axes[0].legend(loc="lower left", fontsize=9)
    methods = list(metrics["results"]["physical_injection"])
    values = [
        metrics["results"]["physical_injection"][name][
            "false_positives_per_1000_normal"
        ]
        for name in methods
    ]
    axes[1].barh(methods, values, color=["#0c8274"] + ["#a7b8b1"] * 4, height=0.6)
    axes[1].set(
        xlabel="False alerts / 1,000 normal windows",
        title="Default-threshold operating cost",
    )
    axes[1].invert_yaxis()
    for i, val in enumerate(values):
        axes[1].text(val + 2, i, f"{val:.1f}", va="center", fontsize=9)
    axes[1].set_xlim(0, max(values) * 1.23)
    fig.suptitle(
        "CAN Trace · exploratory CAN-MIRGU sample evaluation",
        x=0.03,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    fig.text(
        0.03,
        0.015,
        "One vehicle; derived capture is dependent. Benign-only calibration. High AP does not eliminate false alerts.",
        fontsize=9,
        color="#687d73",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    folder = ROOT / "docs/media"
    folder.mkdir(exist_ok=True)
    fig.savefig(
        folder / "evaluation-plots.png", dpi=170, bbox_inches="tight", facecolor="white"
    )


if __name__ == "__main__":
    main()
