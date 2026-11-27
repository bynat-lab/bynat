import pandas as pd

from bynat.cleaning import BaseData


def test_basedata_extract_keywords_helper(tmp_path):
    frame = BaseData(
        {
            "id": [1, 2],
            "description": ["Blue shoes", "red shirt"],
            "items": [["A", "B"], ["C", "D"]],
            "group": ["x", "x"],
            "score": [1, None],
            "left": ["a", "b"],
            "right": ["c", "d"],
        },
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    keywords = frame.extract_keywords("description", colors=["blue", "red"])
    assert keywords["colors"].tolist() == ["Blue", "Red"]

    pd.testing.assert_frame_equal(frame, original)
