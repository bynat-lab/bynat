import importlib

import numpy as np
import pytest

pytestmark = pytest.mark.unit


def test_profiling_private_dedupe_key_normalizes_unhashable_values():
    from bynat.profiling._internal.computations import dedupe_key

    assert dedupe_key([1, 2]) == "[1, 2]"
    assert dedupe_key({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'
    assert dedupe_key({2, 1}) == "[1, 2]"
    assert dedupe_key(np.array([1, 2])) == "[1, 2]"
    assert dedupe_key(5) == 5


def test_profiling_private_dedupe_key_is_bound_to_canonical_internal_helper():
    import bynat._internal as internal

    computations = importlib.import_module("bynat.profiling._internal.computations")

    assert computations.dedupe_key is internal.dedupe_key
    assert computations.dedupe_key.__module__ == "bynat._internal.keys"
