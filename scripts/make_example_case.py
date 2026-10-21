"""Generate a fully redistributable synthetic case through the real MPS path."""

from pathlib import Path
import csv
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cantrace.data import Encoder, sha256
from cantrace.conditional import ConditionalMPS
from cantrace.forensics import package_case
from cantrace.live import StreamDetector
from cantrace.synthetic import generate


def main():
    clean = generate(1200, seed=19)
    encoder = Encoder(context="same_id").fit(clean[:600])
    train, _, _ = encoder.transform(clean[:600], stride=4)
    cal, _, _ = encoder.transform(clean[600:], stride=4)
    model = ConditionalMPS(rank=2, max_per_id=8).fit(train)
    model.calibrate(cal)
    modelpath = ROOT / "artifacts/synthetic_example_model.npz"
    model.save(modelpath, encoder.metadata())
    frames = generate(500, attack="fuzzing", seed=21)
    source = ROOT / "artifacts/synthetic_example.csv"
    with source.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "can_id", "data", "label"])
        for frame in frames:
            writer.writerow(
                [
                    frame.timestamp,
                    f"{frame.arbitration_id:03X}",
                    bytes(frame.data).hex(),
                    frame.label,
                ]
            )
    detector = StreamDetector(model, encoder)
    for frame in frames:
        result = detector.feed(frame)
        if result and frame.label:
            import numpy as np
            from cantrace.data import FEATURES

            explanation = model.explain(np.array(result.pop("features")), FEATURES, 4)
            bundle = package_case(
                [{**result, "explanation": explanation}],
                sha256(source),
                sha256(modelpath),
                {
                    "source": "generated synthetic fuzzing fixture; not vehicle benchmark data",
                    "encoder": encoder.metadata(),
                    "rank": 2,
                    "threshold": 1,
                },
            )
            (ROOT / "artifacts/example-case.json").write_text(
                json.dumps(bundle, indent=2)
            )
            print("Created actual-MPS synthetic case:", bundle["case_sha256"])
            break


if __name__ == "__main__":
    main()
