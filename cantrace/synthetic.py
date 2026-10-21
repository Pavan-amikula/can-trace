"""Controlled software-only fixtures; these are not automotive benchmark data."""

import numpy as np
from .data import Frame


def generate(n=12000, attack=None, seed=17):
    rng = np.random.default_rng(seed)
    frames = []
    history = {}
    for i in range(n):
        can_id = [0x120, 0x130, 0x240, 0x350][i % 4]
        signal = int(120 + 50 * np.sin(i / 190))
        data = [signal, 255 - signal, (i // 4) % 256, 0, 12, 34, 56, 78]
        data[3] = sum(data[:3]) % 256
        t = i * 0.001 + float(rng.uniform(0, 0.00005))
        active = attack is not None and n * 0.4 <= i < n * 0.65
        label = 0
        if active and i % 4 == 0:
            label = 1
            if attack == "fuzzing":
                data = rng.integers(0, 256, 8).tolist()
            elif attack == "spoofing":
                can_id, data = 0x666, [255] * 8
            elif attack == "masquerade":
                data[0], data[1] = 240, 15
            elif attack == "replay":
                data = list(history.get(i % 100, data))
            elif attack == "dos":
                can_id, data = 0, [0] * 8
            else:
                raise ValueError(f"unknown scenario: {attack}")
        history[i % 100] = (
            tuple(data) if not active else history.get(i % 100, tuple(data))
        )
        frames.append(Frame(t, can_id, tuple(data), label, i + 1))
        if active and attack == "dos":
            frames.extend(
                Frame(t + j * 0.00001, 0, (0,) * 8, 1, i + 1) for j in range(1, 5)
            )
    return frames


if __name__ == "__main__":
    import argparse
    import csv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attack", choices=["dos", "fuzzing", "spoofing", "replay", "masquerade"]
    )
    parser.add_argument("--frames", type=int, default=12000)
    parser.add_argument("--output", required=True, help="canonical CSV destination")
    args = parser.parse_args()
    if not 100 <= args.frames <= 1_000_000:
        parser.error("--frames must be 100..1000000")
    with open(args.output, "x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "can_id", "data", "label"])
        for f in generate(args.frames, attack=args.attack):
            writer.writerow(
                [f.timestamp, f"{f.arbitration_id:03X}", bytes(f.data).hex(), f.label]
            )
