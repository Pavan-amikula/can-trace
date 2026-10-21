import itertools
import numpy as np

from cantrace.tensor import (
    product_state,
    add_states,
    compress,
    contract,
    inner,
    MPSDetector,
)
from cantrace.conditional import ConditionalMPS


def dense(cores):
    a = cores[0][0]
    for core in cores[1:]:
        a = np.tensordot(a, core, axes=(-1, 0))
    return a[..., 0]


def test_mps_addition_compression_matches_dense_reference():
    a, b = product_state([0.1, 0.2, 0.3, 0.4]), product_state([0.8, 0.7, 0.6, 0.5])
    summed = add_states(a, b)
    compressed, loss = compress(summed, 8)
    expected = dense(a) + dense(b)
    np.testing.assert_allclose(dense(compressed), expected, atol=1e-12)
    np.testing.assert_allclose(
        inner(compressed, compressed), np.sum(expected**2), atol=1e-12
    )
    assert loss < 1e-20
    x = np.array([[0.3, 0.8, 0.1, 0.7]])
    expected_overlap = float(np.sum(expected * dense(product_state(x[0]))))
    np.testing.assert_allclose(
        contract(compressed, x, 0.9), expected_overlap, atol=1e-12
    )


def test_rank_cap_and_nonnegative_discarded_energy():
    rng = np.random.default_rng(3)
    state = product_state(rng.random(10))
    for _ in range(8):
        state, loss = compress(add_states(state, product_state(rng.random(10))), 2)
        assert loss >= 0
        assert all(c.shape[0] <= 2 and c.shape[2] <= 2 for c in state)


def test_serialization_and_attribution_match_direct_intervention(tmp_path):
    rng = np.random.default_rng(9)
    x = rng.random((30, 6))
    model = MPSDetector(rank=3, clusters=2, max_train=20).fit(x)
    model.calibrate(x)
    path = tmp_path / "model.npz"
    model.save(path, {"window": 2})
    restored, meta = MPSDetector.load(path)
    np.testing.assert_allclose(
        restored.score_samples(x), model.score_samples(x), atol=1e-12
    )
    explanation = model.explain(x[0], ["a", "b", "c"], 2)
    changed = x[0].copy()
    changed[0] = model.reference[0]
    expected = model.score_samples(x[:1])[0] - model.score_samples(changed[None])[0]
    assert abs(explanation["matrix"][0][0] - expected) < 1e-12
    assert all(
        0 <= h <= np.log2(3) + 1e-10 for group in model.bond_entropies() for h in group
    )
