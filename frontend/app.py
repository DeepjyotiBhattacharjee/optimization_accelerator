import streamlit as st
import pandas as pd
import sqlite3
import json
import requests
from datetime import datetime
import numpy as np


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("🧠 Optimization Modeling Studio")


# =====================================================
# DATABASE INIT
# =====================================================

def init_db():
    conn = sqlite3.connect("models.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at TEXT,
            model_json TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# =====================================================
# JSON SAFE CONVERSION
# =====================================================

def convert_numpy(obj):
    if isinstance(obj, dict):
        return {convert_numpy(k): convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy(i) for i in obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    else:
        return obj


def make_json_safe(model_dict):

    safe = {}

    safe_datasets = {}
    for name, df in model_dict["datasets"].items():
        safe_datasets[name] = convert_numpy(df.to_dict(orient="records"))
    safe["datasets"] = safe_datasets

    safe_parameters = {}
    for pname, pvals in model_dict["parameters"].items():
        new_param = {}
        for key, value in pvals.items():
            if isinstance(key, tuple):
                new_key = "|".join(map(str, key))
            else:
                new_key = str(key)
            new_param[new_key] = convert_numpy(value)
        safe_parameters[pname] = new_param

    safe["parameters"] = safe_parameters
    safe["sets"] = convert_numpy(model_dict["sets"])
    safe["variables"] = convert_numpy(model_dict["variables"])
    safe["constraints"] = convert_numpy(model_dict["constraints"])
    safe["objective"] = model_dict["objective"]

    return safe


# =====================================================
# SESSION INIT
# =====================================================

def init_state():
    defaults = {
        "step": 1,
        "datasets": {},
        "sets": {},
        "parameters": {},
        "variables": [],
        "constraints": [],
        "objective": "",
        "solution": None,
        "objective_value": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# =====================================================
# STEPS
# =====================================================

steps = [
    "1️⃣ Upload Data",
    "2️⃣ Define Sets",
    "3️⃣ Define Parameters",
    "4️⃣ Define Variables",
    "5️⃣ Objective",
    "6️⃣ Constraints",
    "7️⃣ Validate & Solve"
]

st.subheader(steps[st.session_state.step - 1])


# =====================================================
# STEP 1 — UPLOAD
# =====================================================

if st.session_state.step == 1:

    uploaded = st.file_uploader("Upload CSV files", accept_multiple_files=True)

    if uploaded:
        for file in uploaded:
            df = pd.read_csv(file)
            name = file.name.replace(".csv", "")
            st.session_state.datasets[name] = df

    for name, df in st.session_state.datasets.items():
        st.markdown(f"**{name}**")
        st.dataframe(df.head())

    if st.session_state.datasets:
        if st.button("Next ➡", key="step1_next"):
            st.session_state.step = 2


# =====================================================
# STEP 2 — SETS
# =====================================================

elif st.session_state.step == 2:

    for name, df in st.session_state.datasets.items():
        use_set = st.checkbox(f"Use {name} as set", key=f"set_{name}")
        if use_set:
            col = st.selectbox(f"Column for {name}", df.columns, key=f"col_{name}")
            st.session_state.sets[name] = list(df[col].unique())

    st.json(st.session_state.sets)

    if st.session_state.sets:
        if st.button("Next ➡", key="step2_next"):
            st.session_state.step = 3


# =====================================================
# STEP 3 — PARAMETERS
# =====================================================

elif st.session_state.step == 3:

    param_name = st.text_input("Parameter Name")
    dataset = st.selectbox("Dataset", list(st.session_state.datasets.keys()))
    df = st.session_state.datasets[dataset]

    index_cols = st.multiselect("Index Columns", df.columns)
    value_col = st.selectbox("Value Column", df.columns)

    if st.button("Add Parameter"):
        param_dict = {}
        for _, row in df.iterrows():
            key = tuple(row[col] for col in index_cols)
            if len(key) == 1:
                key = key[0]
            param_dict[key] = row[value_col]
        st.session_state.parameters[param_name] = param_dict

    st.write("Current Parameters:", list(st.session_state.parameters.keys()))

    if st.session_state.parameters:
        if st.button("Next ➡", key="step3_next"):
            st.session_state.step = 4


# =====================================================
# STEP 4 — VARIABLES
# =====================================================

elif st.session_state.step == 4:

    var_name = st.text_input("Variable Name")
    var_sets = st.multiselect("Index Sets", list(st.session_state.sets.keys()))
    var_type = st.selectbox("Type", ["Continuous", "Integer", "Binary"])

    st.markdown("### Optional Domain Filter")

    filter_dataset = st.selectbox(
        "Filter Dataset",
        ["-- None --"] + list(st.session_state.datasets.keys())
    )

    filter_def = None

    if filter_dataset != "-- None --":
        df_filter = st.session_state.datasets[filter_dataset]
        filter_column = st.selectbox("Filter Column", df_filter.columns)
        filter_value = st.text_input("Filter Value")

        if filter_value:
            sample_val = df_filter[filter_column].iloc[0]
            cast_val = type(sample_val)(filter_value)
            filter_def = {
                "dataset": filter_dataset,
                "column": filter_column,
                "value": cast_val
            }

    if st.button("Add Variable"):
        var_def = {
            "name": var_name,
            "index": var_sets,
            "type": var_type
        }
        if filter_def:
            var_def["filter"] = filter_def
        st.session_state.variables.append(var_def)

    st.json(st.session_state.variables)

    if st.session_state.variables:
        if st.button("Next ➡", key="step4_next"):
            st.session_state.step = 5


# =====================================================
# STEP 5 — OBJECTIVE
# =====================================================

elif st.session_state.step == 5:

    obj_var = st.selectbox(
        "Variable",
        [v["name"] for v in st.session_state.variables]
    )

    obj_param = st.selectbox(
        "Parameter",
        list(st.session_state.parameters.keys())
    )

    selected_var = next(v for v in st.session_state.variables if v["name"] == obj_var)
    index_sets = selected_var["index"]

    if len(index_sets) == 2:
        set1, set2 = index_sets
        generated_obj = (
            f"sum({obj_param}[i,j] * {obj_var}[i,j] "
            f"for i in {set1} for j in {set2})"
        )
    elif len(index_sets) == 1:
        set1 = index_sets[0]
        generated_obj = (
            f"sum({obj_param}[i] * {obj_var}[i] "
            f"for i in {set1})"
        )
    else:
        generated_obj = ""

    st.code(generated_obj)

    if st.button("Save Objective"):
        st.session_state.objective = generated_obj
        st.success("Objective saved.")

    if st.session_state.objective:
        if st.button("Next ➡", key="step5_next"):
            st.session_state.step = 6


# =====================================================
# STEP 6 — CONSTRAINTS
# =====================================================

elif st.session_state.step == 6:

    expr = None

    var_choice = st.selectbox(
        "Variable",
        [v["name"] for v in st.session_state.variables]
    )

    selected_var = next(v for v in st.session_state.variables if v["name"] == var_choice)
    var_indices = selected_var["index"]

    constraint_dim = st.selectbox("Constraint dimension", var_indices)

    comparator = st.selectbox("Comparator", ["<=", ">=", "=="])

    rhs_param = st.selectbox("RHS Parameter", list(st.session_state.parameters.keys()))

    rhs_multiplier = st.selectbox(
        "Multiply RHS by Variable (optional)",
        ["-- None --"] + [v["name"] for v in st.session_state.variables]
    )

    if len(var_indices) == 2:

        set1, set2 = var_indices

        if constraint_dim == set1:

            if rhs_multiplier != "-- None --":

                multiplier_var = next(
                    v for v in st.session_state.variables
                    if v["name"] == rhs_multiplier
                )

                if len(multiplier_var["index"]) == 1:
                    expr = (
                        f"sum({var_choice}[s,c] for c in {set2}) "
                        f"{comparator} {rhs_param}[s] * {rhs_multiplier}[s] "
                        f"for s in {set1}"
                    )
                else:
                    expr = (
                        f"sum({var_choice}[s,c] for c in {set2}) "
                        f"{comparator} {rhs_param}[s] * {rhs_multiplier}[s,c] "
                        f"for s in {set1}"
                    )
            else:
                expr = (
                    f"sum({var_choice}[s,c] for c in {set2}) "
                    f"{comparator} {rhs_param}[s] "
                    f"for s in {set1}"
                )

        elif constraint_dim == set2:
            expr = (
                f"sum({var_choice}[s,c] for s in {set1}) "
                f"{comparator} {rhs_param}[c] "
                f"for c in {set2}"
            )

    if st.button("Add Constraint"):
        if expr is None:
            st.error("Constraint could not be generated.")
        else:
            st.session_state.constraints.append(expr)

    for idx, c in enumerate(st.session_state.constraints):
        col1, col2 = st.columns([4, 1])
        col1.code(c)
        if col2.button("❌", key=f"del_{idx}"):
            st.session_state.constraints.pop(idx)
            st.experimental_rerun()

    if st.session_state.constraints:
        if st.button("Next ➡", key="step6_next"):
            st.session_state.step = 7


# =====================================================
# STEP 7 — SOLVE
# =====================================================

elif st.session_state.step == 7:

    if st.button("Solve Model"):

        model_def = {
            "datasets": st.session_state.datasets,
            "sets": st.session_state.sets,
            "parameters": st.session_state.parameters,
            "variables": st.session_state.variables,
            "objective": st.session_state.objective,
            "constraints": st.session_state.constraints
        }

        safe_model = make_json_safe(model_def)

        response = requests.post(
            "http://localhost:8000/solve",
            json=safe_model
        )

        if response.status_code == 200:
            result = response.json()
            st.session_state.objective_value = result["objective"]

            rows = []
            for var_name, var_values in result["solution"].items():
                for key, val in var_values.items():
                    rows.append({
                        "variable": var_name,
                        "index": key,
                        "value": val
                    })

            st.session_state.solution = pd.DataFrame(rows)

        else:
            st.error(response.text)


# =====================================================
# RESULTS
# =====================================================

if st.session_state.solution is not None:

    st.markdown("---")
    st.header("📊 Optimization Results")

    col1, col2 = st.columns(2)

    col1.metric("Objective Value", round(st.session_state.objective_value, 2))
    col2.metric("Active Variables",
                len(st.session_state.solution[
                    st.session_state.solution["value"] > 0
                ]))

    st.dataframe(st.session_state.solution)

    st.download_button(
        "Download Solution CSV",
        st.session_state.solution.to_csv(index=False),
        "solution.csv"
    )
