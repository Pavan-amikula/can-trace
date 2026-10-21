"""ID-conditioned MPS normality bank, with benign-only per-ID calibration."""

import json
import numpy as np

from .data import FEATURES
from .tensor import MPSDetector, product_state, add_states, compress, inner, contract


def identifiers(x):
    # Last message's 11 binary identifier sites. Bits never use test labels.
    return np.rint(
        x[:, -len(FEATURES) : -len(FEATURES) + 11] @ (2 ** np.arange(10, -1, -1))
    ).astype(int)


class ConditionalMPS:
    def __init__(self, rank=4, max_per_id=48, angle=0.9):
        self.rank, self.max_per_id, self.angle = rank, max_per_id, angle
        self.models, self.references, self.scales = {}, {}, {}
        self.threshold = 1.0
        self.quantile = 0.99

    def fit(self, x):
        ids = identifiers(x)
        self.training_indices = []
        self.models, self.references, self.scales = {}, {}, {}
        for key in sorted(set(ids)):
            indices = np.flatnonzero(ids == key)
            selected = indices[
                np.linspace(
                    0, len(indices) - 1, min(len(indices), self.max_per_id), dtype=int
                )
            ]
            self.training_indices.extend(selected.tolist())
            group = x[selected]
            state = product_state(group[0], self.angle)
            for row in group[1:]:
                state, _ = compress(
                    add_states(state, product_state(row, self.angle)), self.rank
                )
            state[0] /= max(np.sqrt(inner(state, state)), 1e-15)
            self.models[int(key)] = state
            self.references[int(key)] = np.median(group, axis=0)
        self.reference = np.median(x, axis=0)
        return self

    def raw_score(self, key, x):
        return -np.log(
            np.clip(np.abs(contract(self.models[key], x, self.angle)), 1e-15, 1)
        )

    def calibrate(self, clean, quantile=0.99):
        self.quantile = quantile
        ids = identifiers(clean)
        for key in self.models:
            group = clean[ids == key]
            if len(group) < 2:
                # No supported benign calibration: fail rather than invent a threshold.
                raise ValueError(
                    f"insufficient benign calibration for CAN ID {key:03X}"
                )
            self.scales[key] = max(
                float(
                    np.quantile(self.raw_score(key, group), quantile, method="higher")
                ),
                1e-8,
            )
        return self.threshold

    def score_samples(self, x):
        ids = identifiers(x)
        s = np.full(
            len(x), 2.0
        )  # explicit unknown-ID novelty policy, not a learned probability
        for key in set(ids):
            key = int(key)
            if key in self.models:
                mask = ids == key
                s[mask] = self.raw_score(key, x[mask]) / self.scales[key]
        return s

    def explain(self, x, feature_names, window):
        key = int(identifiers(x[None])[0])
        base = float(self.score_samples(x[None])[0])
        if key not in self.models:
            return {
                "score": base,
                "threshold": 1.0,
                "method": "unknown ID novelty rule; no learned attribution",
                "features": [],
                "matrix": np.zeros((window, len(feature_names))).tolist(),
            }
        # Hold the conditioning ID fixed, so identifier edits do not switch models.
        replaced = np.tile(x, (len(x), 1))
        np.fill_diagonal(replaced, self.references[key])
        deltas = base - self.raw_score(key, replaced) / self.scales[key]
        records = [
            {
                "offset": i // len(feature_names) - window + 1,
                "feature": feature_names[i % len(feature_names)],
                "value": float(x[i]),
                "reference": float(self.references[key][i]),
                "delta": float(deltas[i]),
            }
            for i in range(len(x))
        ]
        return {
            "score": base,
            "threshold": 1.0,
            "conditioning_id": f"0x{key:03X}",
            "method": "ID held fixed; signed per-ID median-replacement score delta; non-additive and non-causal",
            "features": sorted(records, key=lambda r: abs(r["delta"]), reverse=True),
            "matrix": deltas.reshape(window, -1).tolist(),
        }

    @property
    def clusters(self):
        return len(self.models)

    @property
    def parameters(self):
        return sum(c.size for m in self.models.values() for c in m)

    def bond_entropies(self):
        helper = MPSDetector()
        helper.models = list(self.models.values())
        return helper.bond_entropies()

    def save(self, path, encoder_meta):
        keys = sorted(self.models)
        meta = {
            "kind": "id-conditioned",
            "keys": keys,
            "rank": self.rank,
            "angle": self.angle,
            "max_per_id": self.max_per_id,
            "threshold": 1.0,
            "quantile": self.quantile,
            "order": len(self.reference),
            "encoder": encoder_meta,
            "scales": self.scales,
        }
        cores = [c for key in keys for c in self.models[key]]
        # Pack arrays together to avoid thousands of ZIP headers for small cores.
        np.savez_compressed(
            path,
            metadata=json.dumps(meta),
            reference=self.reference,
            references=np.stack([self.references[key] for key in keys]),
            shapes=np.array([c.shape for c in cores], dtype=np.int32),
            weights=np.concatenate([c.reshape(-1) for c in cores]),
        )

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["metadata"]))
            obj = cls(meta["rank"], meta["max_per_id"], meta["angle"])
            obj.quantile = meta["quantile"]
            obj.reference = data["reference"].copy()
            obj.scales = {int(k): v for k, v in meta["scales"].items()}
            obj.references = {
                key: data["references"][i].copy() for i, key in enumerate(meta["keys"])
            }
            if "weights" in data:
                weights, shapes = data["weights"], data["shapes"]
                offsets = np.cumsum([0] + [int(np.prod(shape)) for shape in shapes])
                cores = [
                    weights[offsets[i] : offsets[i + 1]].reshape(tuple(shape)).copy()
                    for i, shape in enumerate(shapes)
                ]
                obj.models = {
                    key: cores[i * meta["order"] : (i + 1) * meta["order"]]
                    for i, key in enumerate(meta["keys"])
                }
            else:
                obj.models = {
                    key: [data[f"m{key}_c{i}"].copy() for i in range(meta["order"])]
                    for key in meta["keys"]
                }
        return obj, meta["encoder"]
