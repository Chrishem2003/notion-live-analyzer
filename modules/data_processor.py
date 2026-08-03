import security_guard
import security_guard
mport pandas as pd
import numpy as np

def infer_column_types(df: pd.DataFrame) -> dict:
    types = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            types[col] = "Numeric"
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            types[col] = "DateTime"
        elif pd.api.types.is_bool_dtype(df[col]):
            types[col] = "Boolean"
        else:
            types[col] = "Categorical / Text"
    return types

def profile_dataset(df: pd.DataFrame) -> dict:
    numeric = df.select_dtypes(include=np.number).columns.tolist()
    categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()
    return {
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "row_count": len(df),
        "col_count": len(df.columns)
    }
