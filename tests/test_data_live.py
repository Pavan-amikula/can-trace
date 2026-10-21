import numpy as np
import pytest

from cantrace.data import Encoder, Frame, load_frames
from cantrace.live import StreamDetector
from cantrace.synthetic import generate
from cantrace.conditional import ConditionalMPS


def test_strict_parser_preserves_line_numbers_and_variable_dlc(tmp_path):
    path = tmp_path / "trace.log"
    path.write_text("# comment\n(1.0) can0 07F#00C30000 1\n(1.01) can0 130#00 0\n")
    f = load_frames(path)
    assert f[0].arbitration_id == 127 and f[0].line == 2
    assert len(f[0].data) == 4 and f[0].label == 1
    path.write_text("(1.0) can0 130#0 0\n")
    with pytest.raises(ValueError, match=":1:"):
        load_frames(path)
    path.write_text("(1.0) can0 130#00 0\n(0.9) can0 130#00 0\n")
    with pytest.raises(ValueError, match="timestamps decrease"):
        load_frames(path)


@pytest.mark.parametrize("context", ["chronological", "same_id"])
def test_stream_batch_parity_and_future_independence(context):
    f = generate(160)
    encoder = Encoder(4, context=context).fit(f[:80])
    x, y, ends = encoder.transform(f)

    class Dummy:
        threshold = 0.2

        def score_samples(self, x):
            return x.mean(axis=1)

    stream = StreamDetector(Dummy(), encoder)
    emitted = [value for frame in f if (value := stream.feed(frame)) is not None]
    np.testing.assert_allclose(
        np.array([e["features"] for e in emitted]), x, atol=1e-12
    )
    short, _, _ = encoder.transform(f[:100])
    np.testing.assert_allclose(short, x[: len(short)])
    flipped = [
        Frame(a.timestamp, a.arbitration_id, a.data, 1 - a.label, a.line) for a in f
    ]
    np.testing.assert_array_equal(encoder.transform(flipped)[0], x)


def test_conditional_save_unknown_id_and_normal_calibration(tmp_path):
    frames = generate(400)
    enc = Encoder(context="same_id").fit(frames)
    x, _, _ = enc.transform(frames, stride=4)
    model = ConditionalMPS(rank=2, max_per_id=6).fit(x)
    model.calibrate(x)
    path = tmp_path / "model.npz"
    model.save(path, enc.metadata())
    restored, metadata = ConditionalMPS.load(path)
    np.testing.assert_allclose(model.score_samples(x), restored.score_samples(x))
    assert metadata["context"] == "same_id"
    unknown = x[:1].copy()
    unknown[0, -22:-11] = 1
    assert model.score_samples(unknown)[0] == 2


@pytest.mark.parametrize(
    "attack", ["dos", "fuzzing", "spoofing", "replay", "masquerade"]
)
def test_all_scenarios_are_labelled_and_chronological(attack):
    frames = generate(400, attack=attack)
    assert any(f.label for f in frames)
    assert all(a.timestamp <= b.timestamp for a, b in zip(frames, frames[1:]))
    assert all(len(f.data) <= 8 for f in frames)
