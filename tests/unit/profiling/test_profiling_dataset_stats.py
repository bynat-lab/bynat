import pandas as pd


def test_missing_values_and_proportions():
    df = pd.DataFrame(
        {
            "c1": [1, None, 3, None],
            "c2": ["a", "b", None, None],
            "c3": [10, 20, 30, 40],
        }
    )
    rep = df.bynat.profile()

    assert rep.dataset.row_count == 4
    assert rep.dataset.column_count == 3
    assert rep.dataset.total_cells == 12
    assert rep.dataset.missing_count == 4
    assert rep.dataset.missing_proportion == 4 / 12

    assert rep.columns["c1"].count == 2
    assert rep.columns["c1"].missing_count == 2
    assert rep.columns["c1"].missing_proportion == 0.5

    assert rep.columns["c3"].count == 4
    assert rep.columns["c3"].missing_count == 0
    assert rep.columns["c3"].missing_proportion == 0.0


def test_duplicate_rows_counting_semantics():
    df = pd.DataFrame(
        {
            "id": [1, 2, 1, 2, 3],
            "val": ["x", "y", "x", "y", "z"],
        }
    )
    rep = df.bynat.profile()

    assert rep.dataset.row_count == 5
    assert rep.dataset.duplicate_rows == 2
    assert rep.dataset.duplicate_proportion == 2 / 5

    df_distinct = pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
    rep_distinct = df_distinct.bynat.profile()
    assert rep_distinct.dataset.duplicate_rows == 0
    assert rep_distinct.dataset.duplicate_proportion == 0.0


def test_duplicate_rows_with_unhashable_cells():
    df = pd.DataFrame(
        {
            "meta": [{"env": "prod"}, {"env": "dev"}, {"env": "prod"}],
            "tags": [["a", "b"], ["c"], ["a", "b"]],
        }
    )
    rep = df.bynat.profile()

    assert rep.dataset.row_count == 3
    assert rep.dataset.duplicate_rows == 1
    assert rep.dataset.duplicate_proportion == 1 / 3
    assert rep.columns["meta"].distinct_count == 2
    assert rep.columns["tags"].distinct_count == 2
