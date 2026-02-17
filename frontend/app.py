import streamlit as st
import pandas as pd
import sqlite3
import json
import requests
from datetime import datetime

st.set_page_config(layout="wide")
st.title("🧠 Optimization Modeling Studio")

# =====================================================
# DATABASE SETUP
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
# SAFE SERIALIZATION
# =====================================================

def make_json_safe(model_dict):

    safe = {}

    # Convert datasets
    safe_datasets = {}
    for name, df in model_dict["datasets"].items():
        safe_datasets[name] = df.to_dict(orient="records")
    safe["datasets"] = safe_datasets

    # Convert parameters (tuple keys → string)
    safe_parameters = {}
    for pname, pvals in model_dict["parameters"].items():
        new_param = {}
        for key, value in pvals.items():
            if isinstance(key, tuple):
                new_key = "|".join(map(str, key))
            else:
                new_key = str(key)
            new_param[new_key] = value
        safe_parameters[pname] = new_param
    safe["parameters"] = safe_parameters

    # Copy remaining safely
    safe["sets"] = model_dict["sets"]
    safe["variables"] = model_dict["variables"]
    safe["constraints"] = model_dict["constraints"]
    safe["objective"] = model_dict["objective"]

    return safe


def save_model(name, model_dict):
    safe_model = make_json_safe(model_dict)
    conn = sqlite3.connect("models.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO models (name, created_at, model_json)
        VALUES (?, ?, ?)
    """, (name, datetime.now().isoformat(), json.dumps(safe_model)))
    conn.commit()
    conn.close()

# =====================================================
# SESSION STATE INIT
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
# WIZARD HEADER
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
        if st.button("Next ➡"):
            st.session_state.step = 2

# =====================================================
# STEP 2 — SETS
# =====================================================

elif st.session_state.step == 2:

    for name, df in st.session_state.datasets.items():
        use_set = st.checkbox(f"Use {name} as set")
        if use_set:
            col = st.selectbox(f"Column for {name}", df.columns)
            st.session_state.sets[name] = list(df[col].unique())

    st.json(st.session_state.sets)

    if st.session_state.sets:
        if st.button("Next ➡"):
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
        if st.button("Next ➡"):
            st.session_state.step = 4

# =====================================================
# STEP 4 — VARIABLES (WITH DOMAIN FILTER)
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
        if st.button("Next ➡"):
            st.session_state.step = 5

# =====================================================
# STEP 5 — OBJECTIVE (AUTO)
# =====================================================

elif st.session_state.step == 5:

    obj_var = st.selectbox("Variable", [v["name"] for v in st.session_state.variables])
    obj_param = st.selectbox("Parameter", list(st.session_state.parameters.keys()))

    selected_var = next(v for v in st.session_state.variables if v["name"] == obj_var)
    index_sets = selected_var["index"]

    loops = " ".join([f"for {s} in {s}" for s in index_sets])
    index_access = ",".join(index_sets)

    st.session_state.objective = f"sum({obj_param}[{index_access}] * {obj_var}[{index_access}] {loops})"

    st.code(st.session_state.objective)

    if st.button("Next ➡"):
        st.session_state.step = 6

# =====================================================
# STEP 6 — CONSTRAINTS
# =====================================================

elif st.session_state.step == 6:

    var_choice = st.selectbox("Constraint Variable", [v["name"] for v in st.session_state.variables])
    comparator = st.selectbox("Comparator", ["==", "<=", ">="])
    rhs_param = st.selectbox("RHS Parameter", list(st.session_state.parameters.keys()))

    expr = f"{var_choice} {comparator} {rhs_param}"

    if st.button("Add Constraint"):
        st.session_state.constraints.append(expr)

    for i, c in enumerate(st.session_state.constraints):
        col1, col2 = st.columns([4,1])
        col1.code(c)
        if col2.button("❌", key=f"del_{i}"):
            st.session_state.constraints.pop(i)
            st.experimental_rerun()

    if st.session_state.constraints:
        if st.button("Next ➡"):
            st.session_state.step = 7

# =====================================================
# STEP 7 — VALIDATE & SOLVE
# =====================================================

elif st.session_state.step == 7:

    issues = []

    if not st.session_state.sets:
        issues.append("No sets defined.")
    if not st.session_state.parameters:
        issues.append("No parameters defined.")
    if not st.session_state.variables:
        issues.append("No variables defined.")
    if not st.session_state.objective:
        issues.append("No objective defined.")
    if not st.session_state.constraints:
        issues.append("No constraints defined.")

    if issues:
        for issue in issues:
            st.warning(issue)
    else:
        st.success("Model structurally complete.")

        if st.button("Solve Model"):

            model_def = {
                "datasets": st.session_state.datasets,
                "sets": st.session_state.sets,
                "parameters": st.session_state.parameters,
                "variables": st.session_state.variables,
                "objective": st.session_state.objective,
                "constraints": st.session_state.constraints
            }

            save_model("Untitled Model", model_def)

            safe_model = make_json_safe(model_def)

            response = requests.post("http://localhost:8000/solve", json=safe_model)

            if response.status_code == 200:
                result = response.json()
                st.session_state.objective_value = result["objective"]
                st.session_state.solution = pd.DataFrame(result["solution"])
            else:
                st.error(response.text)

# =====================================================
# PROFESSIONAL OUTPUT PANEL
# =====================================================

if st.session_state.solution is not None:

    st.markdown("---")
    st.header("📊 Optimization Results")

    col1, col2, col3 = st.columns(3)

    col1.metric("💰 Objective Value", round(st.session_state.objective_value, 2))
    col2.metric("🔢 Total Variables Returned", len(st.session_state.solution))
    col3.metric("📦 Active Variables",
                len(st.session_state.solution[st.session_state.solution["value"] > 0]))

    st.markdown("### 📋 Solution Details")
    st.dataframe(st.session_state.solution)

    csv = st.session_state.solution.to_csv(index=False).encode()

    st.download_button(
        "⬇ Download Solution CSV",
        csv,
        "solution.csv",
        "text/csv"
    )
