"""Stateful, causal scoring for passive python-can inputs."""

from collections import deque
import numpy as np
from .data import FEATURES, Frame


class StreamDetector:
    def __init__(self, model, encoder):
        self.model, self.encoder = model, encoder
        self.last, self.previous = {}, None
        self.rows = deque(maxlen=encoder.window)
        self.frames = deque(maxlen=encoder.window)
        self.by_id_rows, self.by_id_frames = {}, {}

    def feed(self, frame: Frame):
        if self.previous is not None and frame.timestamp < self.previous:
            raise ValueError("stream timestamp decreased")
        if self.frames and frame.channel != self.frames[-1].channel:
            raise ValueError("one channel per StreamDetector")
        dt = 0 if self.previous is None else frame.timestamp - self.previous
        gap = (
            0
            if frame.arbitration_id not in self.last
            else frame.timestamp - self.last[frame.arbitration_id]
        )
        row = [float((frame.arbitration_id >> bit) & 1) for bit in range(10, -1, -1)]
        row += (
            [b / 255 for b in frame.data]
            + [0] * (8 - len(frame.data))
            + [len(frame.data) / 8]
        )
        row += (
            1 - np.exp(-np.array([dt, gap]) / (3 * self.encoder.gap_scale))
        ).tolist()
        self.previous, self.last[frame.arbitration_id] = (
            frame.timestamp,
            frame.timestamp,
        )
        self.rows.append(row)
        self.frames.append(frame)
        rows, frames = self.rows, self.frames
        if self.encoder.context == "same_id":
            rows = self.by_id_rows.setdefault(
                frame.arbitration_id, deque(maxlen=self.encoder.window)
            )
            frames = self.by_id_frames.setdefault(
                frame.arbitration_id, deque(maxlen=self.encoder.window)
            )
            rows.append(row)
            frames.append(frame)
        if len(rows) < self.encoder.window:
            return None
        x = np.array(rows).reshape(-1)
        score = float(self.model.score_samples(x[None])[0])
        return {
            "score": score,
            "alert": score > self.model.threshold,
            "threshold": self.model.threshold,
            "frames": [f.record() for f in frames],
            "features": x.tolist(),
        }
