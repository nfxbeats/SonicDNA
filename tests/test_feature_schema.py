from sonicdna.feature_schema import FEATURE_VECTOR_LENGTH, validate_schema


def test_schema_is_valid() -> None:
    validate_schema()
    assert FEATURE_VECTOR_LENGTH == 177

