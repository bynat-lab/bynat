import operator
import numpy as np
import pandas as pd
from typing import Any


class Analyzer:
    """
    Provide reusable analytics helpers for dashboard and API responses.

    Notes:
        Methods in this class support a common workflow:
        1. Apply filters.
        2. Compute optional rule-based transformations.
        3. Return serializable data structures for frontend consumption.
    """

    def __init__(self, dataframe: pd.DataFrame):
        """
        Initialize the analyzer with a defensive copy of source data.

        Args:
            dataframe (pd.DataFrame): Input dataset used by analytics methods.

        Returns:
            None
        """
        self.dataframe = dataframe.copy()


    def _is_safe_expression(self, expression: Any) -> bool:
        """
        Perform a lightweight safety check for dynamic eval expressions.

        Notes:
            This is a guardrail, not a full sandbox. It blocks clearly risky
            tokens and non-string payloads before passing expressions to
            `DataFrame.eval`.

        Args:
            expression (Any): Candidate expression text.

        Returns:
            bool: True if the expression passes basic safety checks, otherwise
            False.
        """
        if not isinstance(expression, str):
            return False

        blocked_tokens = ["__", "@", "import", "lambda", ";"]
        lowered = expression.lower()

        return not any(token in lowered for token in blocked_tokens)


    def _apply_filters(self, dataframe: pd.DataFrame, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        """
        Filter a dataframe using equality, membership, and operator predicates.

        Notes:
            - Scalar values apply equality filtering.
            - List values apply membership filtering via `isin`.
            - Dict values apply operator filters, for example:
              `{"salary": {">=": 5000, "<": 10000}}`.
            - Supported operators are: `>`, `<`, `>=`, `<=`, `!=`, `==`,
              and `contains` (case-insensitive literal substring match).
            - Unknown columns are ignored safely.
            - Invalid/unsupported operations are skipped without raising.

        Args:
            dataframe (pd.DataFrame): Dataframe to filter.
            filters (dict[str, Any] | None): Mapping from column name to filter
                value/list. Defaults to None.

        Returns:
            pd.DataFrame: Filtered dataframe.
        """
        if not filters:
            return dataframe
            
        filtered_dataframe = dataframe.copy()

        op_map = {
            '>': operator.gt,
            '<': operator.lt,
            '>=': operator.ge,
            '<=': operator.le,
            '!=': operator.ne,
            '==': operator.eq,
        }

        for col, value in filters.items():
            if col in filtered_dataframe.columns:
                if isinstance(value, list):
                    filtered_dataframe = filtered_dataframe[filtered_dataframe[col].isin(value)]

                elif isinstance(value, dict):
                    col_series = filtered_dataframe[col]

                    for op, val in value.items():
                        if op in op_map or op == 'contains':
                            try:
                                if op == 'contains':
                                    mask = col_series.fillna('').astype(str).str.contains(str(val).strip(), case = False, na = False, regex = False)
                                
                                elif op in {'>', '<', '>=', '<='}:
                                    func = op_map[op]
                                    
                                    left = pd.to_numeric(col_series, errors = 'coerce')
                                    right = pd.to_numeric(pd.Series([val]), errors = 'coerce').iloc[0]

                                    if pd.isna(right):
                                        continue

                                    mask = func(left, right).fillna(False)

                                else:
                                    func = op_map[op]
                                    mask = func(col_series, val)

                                filtered_dataframe = filtered_dataframe[mask]
                                col_series = filtered_dataframe[col]

                            except Exception as e:
                                print(f"Failed to apply filter for col {col!r}, operator {op!r} with value {val!r} Error: {e}")
                                
                                continue
                
                else:
                    filtered_dataframe = filtered_dataframe[filtered_dataframe[col] == value]
                    
        return filtered_dataframe


    def _apply_computed_rules(self, dataframe: pd.DataFrame, rules: list[dict[str, Any]] | None) -> pd.DataFrame:
        """
        Apply dynamic post-processing rules to a dataframe.

        Notes:
            Supported rule styles:
            - Conditional set: `{"where": "...", "set_col": "...", "set_value": ...}`
            - Expression column: `{"new_col": "...", "expression": "..."}`
            - Series method: `{"source_col": "...", "method": "...", "new_col": "..."}`
            Invalid rules are skipped safely.

        Args:
            dataframe (pd.DataFrame): Dataframe to transform.
            rules (list[dict[str, Any]] | None): Rule definitions to apply.

        Returns:
            pd.DataFrame: Transformed dataframe.
        """
        if not rules:
            return dataframe
            
        result_dataframe = dataframe.copy()
        
        for rule in rules:
            if not isinstance(rule, dict):
                continue

            try:
                if "where" in rule:
                    required = {"where", "set_col", "set_value"}
                    if not required.issubset(rule.keys()):
                        continue

                    if not self._is_safe_expression(rule["where"]):
                        continue

                    mask = result_dataframe.eval(rule["where"])
                    result_dataframe.loc[mask, rule["set_col"]] = rule["set_value"]

                elif "expression" in rule:
                    required = {"new_col", "expression"}
                    if not required.issubset(rule.keys()):
                        continue

                    if not self._is_safe_expression(rule["expression"]):
                        continue

                    expr = f"{rule['new_col']} = {rule['expression']}"
                    result_dataframe.eval(expr, inplace = True)

                elif "method" in rule:
                    required = {"source_col", "method", "new_col"}
                    if not required.issubset(rule.keys()):
                        continue

                    src = rule["source_col"]
                    method_name = rule["method"]

                    if src not in result_dataframe.columns:
                        continue

                    method = getattr(result_dataframe[src], method_name, None)
                    if method is None:
                        continue

                    result_dataframe[rule["new_col"]] = method()

            except Exception as e:
                context_key = (
                    "set_col" if "set_col" in rule else
                    "new_col" if "new_col" in rule else
                    "source_col" if "source_col" in rule else
                    "rule"
                )
                context_value = rule.get(context_key, rule)
                print( f"Failed to compute rules for context {context_key!r}, value {context_value!r}. Error: {e}"
                )
                continue
                
        return result_dataframe

    
    def get_categorical_distribution(
            self,
            x_col: str,
            top_n: int | None = None,
            show_others: bool = False,
            filters: dict | None = None,
            rules: list | None = None,
            orient: str = 'records',
            **kwargs
    ) -> dict[str, Any]:
        """
        Return distribution counts for a categorical column.

        Args:
            x_col (str): Categorical column to aggregate.
            top_n (int | None): Optional limit for top categories.
            show_others (bool): If True, collapse categories outside `top_n`
                into an `"Others"` row with a breakdown payload.
            filters (dict | None): Optional pre-aggregation filters.
            rules (list | None): Optional computed rules applied to the result.
            orient (str): Output orientation for `DataFrame.to_dict`.
            **kwargs: Extra metadata merged into the returned response object.

        Returns:
            dict[str, Any]: Response object with a `"data"` key containing the
            serialized distribution rows.

        Example:
        ```
            analyzer.get_categorical_distribution(
                x_col="country",
                top_n=10,
                filters={"contract_type": "Permanent"}
            )
        ```
        """
        data = self._apply_filters(self.dataframe, filters)
        
        if data.empty or x_col not in data.columns: return {"data": []}

        grouped = data[x_col].value_counts().reset_index()
        grouped.columns = ['x', 'y']
        
        if top_n and show_others and len(grouped) > top_n:
            top_df = grouped.head(top_n).copy()
            others_df = grouped.iloc[top_n:].copy()

            others_val = others_df['y'].sum()

            others_breakdown = others_df[['x', 'y']].to_dict(orient = orient)

            others_row = pd.DataFrame({
                'x': ['Others'],
                'y': [others_val],
                'is_others': [True],
                'others_breakdown': [others_breakdown]
            })

            top_df['is_others'] = False
            top_df['others_breakdown'] = None

            grouped = pd.concat([top_df, others_row], ignore_index = True)
            
        elif top_n:
            grouped = grouped.head(top_n)
            
        grouped = self._apply_computed_rules(grouped, rules)

        response =  {"data": grouped.to_dict(orient = orient)}

        if kwargs:
            response.update(kwargs)

        return response
                


    def get_numerical_aggregation(
            self,
            x_col: str,
            y_col: str,
            agg_func: str = 'mean',
            round_value: int = 2,
            top_n: int | None = None,
            show_others: bool = False,
            filters: dict | None = None,
            rules: list | None = None,
            orient: str = 'records',
            **kwargs
    ) -> dict[str, Any]:
        """
        Aggregate a numeric column by category.

        Args:
            x_col (str): Grouping column.
            y_col (str): Numeric column to aggregate.
            agg_func (str): Aggregation function name (for example: `mean`,
                `sum`, `median`, `max`).
            round_value (int): Decimal places used when the aggregated value is
                numeric. Defaults to 2.
            top_n (int | None): Optional cap for highest `y` rows.
            show_others (bool): If True, collapse categories outside `top_n`
                into an `"Others"` row while preserving a breakdown payload.
            filters (dict | None): Optional filters applied before aggregation.
            rules (list | None): Optional computed rules on output rows.
            orient (str): Output orientation for `DataFrame.to_dict`.
            **kwargs: Extra metadata merged into the returned response object.

        Returns:
            dict[str, Any]: Response object with a `"data"` key containing the
            serialized aggregation rows.
        """
        data = self._apply_filters(self.dataframe, filters)
        if data.empty or x_col not in data.columns or y_col not in data.columns: return {"data": []}

        valid_data = data.dropna(subset = [y_col])

        try:
            grouped = valid_data.groupby(x_col)[y_col].agg(agg_func).reset_index()
        except Exception as e:
            print(f"Failed to get numerical aggregation, aggergate function's value: {agg_func!r}, cols: [{x_col!r}, {y_col!r}]. Error: {e}")
            return {"data": []}

        if pd.api.types.is_numeric_dtype(grouped[y_col]):
            grouped[y_col] = grouped[y_col].round(round_value)

        grouped.columns = ['x', 'y']
        grouped = grouped.sort_values(by = 'y', ascending = False)

        if top_n and show_others and len(grouped) > top_n:
            top_df = grouped.head(top_n).copy()
            others_df = grouped.iloc[top_n:].copy()
            others_categories = others_df['x'].tolist()
            others_source = valid_data[valid_data[x_col].isin(others_categories)]

            others_val = others_source[y_col].agg(agg_func)
            if isinstance(others_val, np.generic):
                others_val = others_val.item()
            if isinstance(others_val, float):
                others_val = round(others_val, round_value)

            others_breakdown = others_df[['x', 'y']].to_dict(orient = orient)
            
            others_row = pd.DataFrame({
                'x': ['Others'],
                'y': [others_val],
                'is_others': [True],
                'others_breakdown': [others_breakdown] 
            })

            top_df['is_others'] = False
            top_df['others_breakdown'] = None

            grouped = pd.concat([top_df, others_row], ignore_index = True)
        
        elif top_n:
            grouped = grouped.head(top_n)
            
        grouped = self._apply_computed_rules(grouped, rules)

        response =  {"data": grouped.to_dict(orient = orient)}

        if kwargs:
            response.update(kwargs)

        return response


    def get_time_series(
            self,
            date_col: str,
            time_period: str = 'M',
            num_col: str = None,
            agg_func: str = 'count',
            filters: dict | None = None,
            rules: list | None = None,
            orient: str = 'records',
            **kwargs
    ) -> dict[str, Any]:
        """
        Build a time-series aggregation from a date/datetime column.

        Notes:
            Accepted `time_period` values:
            - `M`: Monthly buckets (`YYYY-MM`)
            - `Y`: Yearly buckets (`YYYY`)
            - `H`: Hourly Buckets (`YYYY-MM-DD HH:00`)
            - Any other value: Daily buckets (`YYYY-MM-DD`)

        Args:
            date_col (str): Source datetime/date column used for time bucketing.
            time_period (str): Time bucket granularity.
            num_col (str | None): Optional numeric column for non-count
                aggregation.
            agg_func (str): Aggregation function for `num_col`.
            filters (dict | None): Optional filters applied before aggregation.
            rules (list | None): Optional computed rules on output rows.
            orient (str): Output orientation for `DataFrame.to_dict`.
            **kwargs: Extra metadata merged into the returned response object.

        Returns:
            dict[str, Any]: Response object with a `"data"` key containing the
            serialized time-series rows.
        """
        data = self._apply_filters(self.dataframe, filters)
        if data.empty or date_col not in data.columns: return {"data": []}

        data = data.dropna(subset = [date_col]).copy()
        data[date_col] = pd.to_datetime(data[date_col], errors = 'coerce')
        data = data.dropna(subset = [date_col])

        if data.empty:
            return {"data": []}
        
        if time_period.upper() == 'M':
            data['time_x'] = data[date_col].dt.to_period('M').dt.to_timestamp()
            freq = 'MS'
            format = '%Y-%m'
            
        elif time_period.upper() == 'Y':
            data['time_x'] = data[date_col].dt.to_period('Y').dt.to_timestamp()
            freq = 'YS'
            format = '%Y'

        elif time_period.upper() == 'H':
            data['time_x'] = data[date_col].dt.floor('h')
            freq = 'h'
            format = '%Y-%m-%d %H:00'
            
        else:
            data['time_x'] = data[date_col].dt.floor('d')
            freq = 'D'
            format = '%Y-%m-%d'

        if num_col and agg_func != 'count':
            if num_col not in data.columns:
                return {"data": []}

            try:
                grouped = data.groupby('time_x')[num_col].agg(agg_func).reset_index()
            except Exception as e:
                print(f"Failed to get time series, aggregate funnction's value: {agg_func!r}, cols: [{date_col!r}, {num_col!r}]. Error: {e}")
                return {"data": []}

            if pd.api.types.is_numeric_dtype(grouped[num_col]):
                grouped[num_col] = grouped[num_col].round(0)
            
            grouped.columns = ['time_x', 'y']
        
        else:
            grouped = data.groupby('time_x').size().reset_index(name = 'y')
            grouped.columns = ['time_x', 'y']

        if not grouped.empty:
            min_date = grouped['time_x'].min()
            max_date = grouped['time_x'].max()
            
            full_date_range = pd.date_range(start = min_date, end = max_date, freq = freq)
            
            grouped = grouped.set_index('time_x').reindex(full_date_range, fill_value = 0).reset_index()
            grouped.columns = ['x', 'y']
            
            grouped['x'] = grouped['x'].dt.strftime(format)
        else:
            grouped.columns = ['x', 'y']

        grouped = grouped.sort_values(by = 'x', ascending = True)
       
        grouped = self._apply_computed_rules(grouped, rules)

        response =  {"data": grouped.to_dict(orient = orient)}

        if kwargs:
            response.update(kwargs)

        return response


    def get_kpi_value(
            self,
            column: str,
            agg_func: str = 'count',
            round_value: int = 2,
            filters: dict | None = None,
            **kwargs
    ) -> dict[str, Any]:
        """
        Compute a single KPI metric.

        Args:
            column (str): Source column used when `agg_func` is not `count`.
            agg_func (str): Aggregation function name; `count` uses row count.
            round_value (int): Decimal places used when the KPI result is a
                floating-point value. Defaults to 2.
            filters (dict | None): Optional filters applied before KPI
                computation.
            **kwargs: Optional metadata fields for the response card. `title`
                customizes the KPI title.

        Returns:
            dict[str, Any]: KPI payload containing `"data"`, `"title"`, and
            any additional metadata.
        """
        data = self._apply_filters(self.dataframe, filters)
        
        if agg_func == 'count':
            value = len(data)
        else:
            if column not in data.columns:
                value = None
            else:
                try:
                    value = data[column].agg(agg_func)
                except Exception as e:
                    print(f"Failed to get kpi value, aggregate funnction's value: {agg_func!r}, col: [{column!r}]. Error: {e}")
                    value = None

        if pd.isna(value):
            value = None
        elif isinstance(value, np.generic):
            value = value.item()
            
        kpi_card = {
            "data": round(value, round_value) if isinstance(value, float) and round_value else int(value) if isinstance(value, (float, np.int64, int)) else value,
            "title": kwargs.pop("title", column)
        }

        if kwargs:
            kpi_card.update(kwargs)

        return kpi_card

    
    def get_bins(
            self,
            col: str,
            bins: int = 10,
            filters: dict = None,
            rules: list = None,
            orient: str = 'records',
            **kwargs
    ) -> dict[str, Any]:
        """
        Create histogram bins for a numeric column.

        Args:
            col (str): Numeric source column.
            bins (int): Number of histogram bins. Defaults to 10.
            filters (dict | None): Optional filters applied before binning.
            rules (list | None): Optional computed rules on output rows.
            orient (str): Output orientation for `DataFrame.to_dict`.
            **kwargs: Extra metadata merged into the returned response object.

        Returns:
            dict[str, Any]: Response object with a `"data"` key containing the
            serialized histogram rows.
        """
        data = self._apply_filters(self.dataframe, filters)
        
        if data.empty or col not in data.columns: return {"data": []}

        if not isinstance(bins, int) or bins <= 0:
            return {"data": []}

        numeric_values = pd.to_numeric(data[col], errors = 'coerce').dropna()
        if numeric_values.empty:
            return {"data": []}

        counts, bin_edges = np.histogram(numeric_values, bins = bins)

        bin_labels = [f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}" for i in range(len(bin_edges) - 1)]
        grouped = pd.DataFrame({'x': bin_labels, 'y': counts})
        
        grouped = self._apply_computed_rules(grouped, rules)
       
        response =  {"data": grouped.to_dict(orient = orient)}

        if kwargs:
            response.update(kwargs)

        return response
