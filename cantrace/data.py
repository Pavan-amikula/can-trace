"""Strict classical CAN parsers, causal features, and capture-local windows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np

PATTERN = re.compile(
    r"^\((\d+(?:\.\d+)?)\)\s+(\S+)\s+([0-9A-Fa-f]{1,8})#([0-9A-Fa-f]{0,16})(?:\s+([01]))?\s*$"
)
FEATURES = (
    [f"id_bit_{i}" for i in range(10, -1, -1)]
    + [f"byte_{i}" for i in range(8)]
    + ["dlc", "bus_gap", "id_gap"]
)


@dataclass(frozen=True)
class Frame:
    timestamp: float
    arbitration_id: int
    data: tuple[int, ...]
    label: int = 0
    line: int = 0
    channel: str = "can0"

    def __post_init__(self):
        if not np.isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("timestamp must be finite and nonnegative")
        if not 0 <= self.arbitration_id <= 0x7FF:
            raise ValueError("only 11-bit classical CAN identifiers are supported")
        if len(self.data) > 8 or any(not 0 <= b <= 255 for b in self.data):
            raise ValueError("classical CAN payload must contain 0..8 bytes")
        if self.label not in (0, 1):
            raise ValueError("label must be 0 or 1")

    def record(self):
        return {
            **asdict(self),
            "can_id": f"0x{self.arbitration_id:03X}",
            "payload": " ".join(f"{b:02X}" for b in self.data),
        }


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frames(path: str | Path) -> list[Frame]:
    """candump/MIRGU log or canonical CSV; reject malformed input with line number.

    CSV fields: timestamp,can_id (hex),data (hex),label (optional 0/1).
    No sorting: acquisition order and original line numbers are evidence.
    """
    path = Path(path)
    frames = []
    with path.open(encoding="utf-8-sig") as stream:
        if path.suffix.lower() == ".csv":
            for i, row in enumerate(csv.DictReader(stream), 2):
                try:
                    frames.append(
                        Frame(
                            float(row["timestamp"]),
                            int(row["can_id"], 16),
                            tuple(bytes.fromhex(row["data"])),
                            int(row.get("label", 0)),
                            i,
                        )
                    )
                except (ValueError, KeyError) as e:
                    raise ValueError(
                        f"{path.name}:{i}: invalid canonical CSV: {e}"
                    ) from e
        else:
            for i, line in enumerate(stream, 1):
                if not line.strip() or line.startswith("#"):
                    continue
                m = PATTERN.fullmatch(line.strip())
                if not m:
                    raise ValueError(f"{path.name}:{i}: unsupported candump frame")
                t, channel, can_id, payload, label = m.groups()
                try:
                    frames.append(
                        Frame(
                            float(t),
                            int(can_id, 16),
                            tuple(bytes.fromhex(payload)),
                            int(label or 0),
                            i,
                            channel,
                        )
                    )
                except ValueError as e:
                    raise ValueError(f"{path.name}:{i}: {e}") from e
    if not frames:
        raise ValueError("empty capture")
    if any(b.timestamp < a.timestamp for a, b in zip(frames, frames[1:])):
        raise ValueError(
            "capture timestamps decrease; preserve and inspect original evidence"
        )
    if len({f.channel for f in frames}) != 1:
        raise ValueError("split multi-channel captures before feature extraction")
    return frames


class Encoder:
    def __init__(self, window=4, context="chronological"):
        self.window = window
        self.context = context
        self.gap_scale = np.ones(2)
        self.seen_ids = []

    @staticmethod
    def raw(frames):
        rows, last, previous = [], {}, None
        for f in frames:
            dt = 0.0 if previous is None else f.timestamp - previous
            same = (
                0.0
                if f.arbitration_id not in last
                else f.timestamp - last[f.arbitration_id]
            )
            rows.append(
                [float((f.arbitration_id >> bit) & 1) for bit in range(10, -1, -1)]
                + list(f.data)
                + [0] * (8 - len(f.data))
                + [len(f.data), dt, same]
            )
            previous, last[f.arbitration_id] = f.timestamp, f.timestamp
        return np.array(rows, dtype=np.float64)

    def fit(self, frames):
        gaps = self.raw(frames)[:, -2:]
        self.gap_scale = np.array(
            [np.median(g[g > 0]) if np.any(g > 0) else 0.001 for g in gaps.T]
        )
        self.seen_ids = sorted({f.arbitration_id for f in frames})
        return self

    def transform(self, frames, stride=1):
        x = self.raw(frames)
        x[:, 11:19] /= 255
        x[:, 19] /= 8
        # Smooth, bounded timing map; all scaling fitted on training traffic only.
        x[:, -2:] = 1 - np.exp(-x[:, -2:] / (3 * self.gap_scale))
        if self.context == "same_id":
            groups = {}
            indices = []
            for i, frame in enumerate(frames):
                history = groups.setdefault(frame.arbitration_id, [])
                history.append(i)
                if (
                    len(history) >= self.window
                    and (len(history) - self.window) % stride == 0
                ):
                    indices.append(history[-self.window :])
            if not indices:
                return (
                    np.empty((0, self.window * len(FEATURES))),
                    np.array([], dtype=int),
                    np.array([], dtype=int),
                )
            ix = np.array(indices)
            windows = x[ix].reshape(len(ix), -1)
            labels = np.array([f.label for f in frames])
            return windows, labels[ix].max(axis=1), ix[:, -1]
        ends = np.arange(self.window - 1, len(x), stride)
        if not len(ends):
            return (
                np.empty((0, self.window * len(FEATURES))),
                np.array([], dtype=int),
                ends,
            )
        windows = np.stack([x[i - self.window + 1 : i + 1].reshape(-1) for i in ends])
        y = np.array(
            [max(f.label for f in frames[i - self.window + 1 : i + 1]) for i in ends]
        )
        return windows, y, ends

    def metadata(self):
        return {
            "window": self.window,
            "context": self.context,
            "gap_scale": self.gap_scale.tolist(),
            "seen_ids": self.seen_ids,
            "features": FEATURES,
        }

    @classmethod
    def restore(cls, meta):
        obj = cls(meta["window"], meta.get("context", "chronological"))
        obj.gap_scale = np.array(meta["gap_scale"])
        obj.seen_ids = meta["seen_ids"]
        return obj
