import sys

import pytest

from bynat.cleaning import BaseData


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        pytest.param({"table_name": " "}, "table_name", id="blank-table-name"),
        pytest.param({"if_exists": "merge"}, "if_exists", id="unsupported-if-exists"),
        pytest.param({"database_type": ""}, "database_type", id="blank-database-type"),
        pytest.param({"database_name": ""}, "SQLite", id="blank-database-name"),
        pytest.param({"database_type": "postgresql", "database_host": ""}, "are required", id="postgres-missing-host"),
        pytest.param(
            {"database_type": "mssql+pyodbc", "database_user": "u", "database_password": "p",
             "database_host": "h", "database_port": "1"},
            "database_driver",
            id="mssql-missing-driver",
        ),
    ],
)
def test_save_to_sql_rejects_invalid_arguments_before_connecting(monkeypatch, tmp_path, kwargs, message):
    monkeypatch.setitem(sys.modules, "sqlalchemy", None)
    arguments = {
        "table_name": "items",
        "database_type": "sqlite",
        "database_user": "",
        "database_password": "",
        "database_host": "",
        "database_port": "",
        "database_name": str(tmp_path / "out.db"),
        "if_exists": "append",
    }
    arguments.update(kwargs)

    with pytest.raises(ValueError, match=message):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_sql(**arguments)
