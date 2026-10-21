"""A deterministic, truncated MPS representation of a kernel mean embedding.

Each sample maps to a product of [cos(theta*x), sin(theta*x)] vectors.
Sums of those product states are compressed by canonical QR/SVD sweeps.
This is a kernel support estimator, not a normalized Born likelihood.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from sklearn.cluster import KMeans


def product_state(x, angle=0.9):
    return [
        np.array([np.cos(angle * v), np.sin(angle * v)]).reshape(1, 2, 1) for v in x
    ]


def add_states(a, b):
    if len(a) != len(b) or len(a) < 2:
        raise ValueError("MPS addition requires equal orders >= 2")
    out = [np.concatenate([a[0], b[0]], axis=2)]
    for x, y in zip(a[1:-1], b[1:-1]):
        c = np.zeros((x.shape[0] + y.shape[0], 2, x.shape[2] + y.shape[2]))
        c[: x.shape[0], :, : x.shape[2]] = x
        c[x.shape[0] :, :, x.shape[2] :] = y
        out.append(c)
    out.append(np.concatenate([a[-1], b[-1]], axis=0))
    return out


def compress(cores, rank):
    """Left orthogonalize, then truncate with a right-to-left SVD sweep."""
    c = [x.copy() for x in cores]
    for i in range(len(c) - 1):
        l, p, r = c[i].shape
        q, rem = np.linalg.qr(c[i].reshape(l * p, r), mode="reduced")
        c[i] = q.reshape(l, p, -1)
        c[i + 1] = np.einsum("ab,bpc->apc", rem, c[i + 1])
    discarded = 0.0
    for i in range(len(c) - 1, 0, -1):
        l, p, r = c[i].shape
        u, s, v = np.linalg.svd(c[i].reshape(l, p * r), full_matrices=False)
        k = min(rank, len(s))
        discarded += float(np.sum(s[k:] ** 2))
        c[i] = v[:k].reshape(k, p, r)
        c[i - 1] = np.einsum("apb,bk->apk", c[i - 1], u[:, :k] * s[:k])
    return c, discarded


def inner(a, b):
    z = np.ones((1, 1))
    for x, y in zip(a, b):
        z = np.einsum("ab,api,bpj->ij", z, x, y, optimize=True)
    return float(z[0, 0])


def contract(cores, x, angle):
    v = np.stack([np.cos(angle * x), np.sin(angle * x)], axis=2)
    z = np.ones((len(x), 1))
    for i, core in enumerate(cores):
        z = (z @ core[:, 0, :]) * v[:, i, 0, None] + (z @ core[:, 1, :]) * v[
            :, i, 1, None
        ]
    return z[:, 0]


class MPSDetector:
    def __init__(self, rank=8, clusters=6, angle=0.9, max_train=768):
        self.rank, self.clusters, self.angle, self.max_train = (
            rank,
            clusters,
            angle,
            max_train,
        )
        self.models = []
        self.threshold = 0.0
        self.discarded_energy = []

    def fit(self, x):
        if x.ndim != 2 or len(x) < self.clusters:
            raise ValueError("insufficient 2D training examples")
        self.reference = np.median(x, axis=0)
        # Regular, chronological subsampling avoids a random training-data lottery.
        sample = x[np.linspace(0, len(x) - 1, min(len(x), self.max_train), dtype=int)]
        self.assignment = KMeans(
            n_clusters=self.clusters, random_state=7, n_init=10
        ).fit_predict(sample)
        self.models, self.discarded_energy = [], []
        for label in range(self.clusters):
            group = sample[self.assignment == label]
            state = product_state(group[0], self.angle)
            lost = 0.0
            for row in group[1:]:
                state, loss = compress(
                    add_states(state, product_state(row, self.angle)), self.rank
                )
                lost += loss
            norm = np.sqrt(inner(state, state))
            state[0] /= max(norm, 1e-15)
            self.models.append(state)
            self.discarded_energy.append(lost)
        return self

    def score_samples(self, x):
        if len(x) == 0:
            return np.array([])
        overlap = np.max(
            np.stack([np.abs(contract(m, x, self.angle)) for m in self.models]), axis=0
        )
        return -np.log(np.clip(overlap, 1e-15, 1.0))

    def calibrate(self, clean, quantile=0.99):
        self.quantile = quantile
        self.threshold = float(
            np.quantile(self.score_samples(clean), quantile, method="higher")
        )
        return self.threshold

    def explain(self, x, feature_names, window):
        """Signed single-feature median-replacement deltas, not additive SHAP."""
        base = float(self.score_samples(x[None])[0])
        replaced = np.tile(x, (len(x), 1))
        np.fill_diagonal(replaced, self.reference)
        deltas = base - self.score_samples(replaced)
        records = [
            {
                "offset": i // len(feature_names) - window + 1,
                "feature": feature_names[i % len(feature_names)],
                "value": float(x[i]),
                "reference": float(self.reference[i]),
                "delta": float(deltas[i]),
            }
            for i in range(len(x))
        ]
        return {
            "score": base,
            "threshold": self.threshold,
            "method": "signed median-replacement score delta; non-additive and non-causal",
            "features": sorted(records, key=lambda r: abs(r["delta"]), reverse=True),
            "matrix": deltas.reshape(window, -1).tolist(),
        }

    def bond_entropies(self):
        output = []
        for state in self.models:
            c = [a.copy() for a in state]  # saved model is right canonical
            entropies = []
            for i in range(len(c) - 1):
                l, p, r = c[i].shape
                u, s, vh = np.linalg.svd(c[i].reshape(l * p, r), full_matrices=False)
                probs = s * s / max(float(np.sum(s * s)), 1e-15)
                entropies.append(
                    float(-np.sum(probs * np.log2(np.maximum(probs, 1e-15))))
                )
                c[i] = u.reshape(l, p, -1)
                c[i + 1] = np.einsum("ab,bpc->apc", s[:, None] * vh, c[i + 1])
            output.append(entropies)
        return output

    @property
    def parameters(self):
        return sum(c.size for m in self.models for c in m)

    def save(self, path, encoder_meta):
        meta = {
            "rank": self.rank,
            "clusters": self.clusters,
            "angle": self.angle,
            "max_train": self.max_train,
            "threshold": self.threshold,
            "quantile": self.quantile,
            "order": len(self.reference),
            "encoder": encoder_meta,
            "discarded_energy": self.discarded_energy,
        }
        arrays = {
            f"m{j}_c{i}": c for j, m in enumerate(self.models) for i, c in enumerate(m)
        }
        np.savez_compressed(
            path, reference=self.reference, metadata=json.dumps(meta), **arrays
        )

    @classmethod
    def load(cls, path):
        # No pickle deserialization, including for externally provided model files.
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["metadata"]))
            obj = cls(
                **{k: meta[k] for k in ("rank", "clusters", "angle", "max_train")}
            )
            obj.threshold, obj.quantile = meta["threshold"], meta["quantile"]
            obj.reference = data["reference"].copy()
            obj.models = [
                [data[f"m{j}_c{i}"].copy() for i in range(meta["order"])]
                for j in range(obj.clusters)
            ]
            obj.discarded_energy = meta["discarded_energy"]
        return obj, meta["encoder"]
