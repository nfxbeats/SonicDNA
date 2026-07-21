import numpy as np

from sonicdna.feature_schema import FEATURE_SCHEMA, FEATURE_VECTOR_LENGTH
from sonicdna.weighting import DEFAULT_WEIGHTS, feature_weight_vector


def test_every_feature_dimension_has_default_weight() -> None:
    vector = feature_weight_vector()
    assert vector.shape == (FEATURE_VECTOR_LENGTH,)
    assert np.all(vector > 0)
    start, end = FEATURE_SCHEMA["low_frequency_body"]
    np.testing.assert_allclose(vector[start:end], DEFAULT_WEIGHTS["body_pitch"])
    assert set(DEFAULT_WEIGHTS.values()) == {1.0}


def test_zero_weight_disables_its_feature_group() -> None:
    vector = feature_weight_vector({"duration": 0.0})
    start, end = FEATURE_SCHEMA["duration"]
    assert np.all(vector[start:end] == 0)
