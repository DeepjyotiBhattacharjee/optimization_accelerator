import pandas as pd
from backend.solver_engine import solve_model

# -------------------------------------------------
# Load REAL CSV DATA
# -------------------------------------------------

customers = pd.read_csv("/Users/deepjyotibhattacharjee/Developer/optimization_accelerator/optimization_data-main/customers.csv")
suppliers = pd.read_csv("/Users/deepjyotibhattacharjee/Developer/optimization_accelerator/optimization_data-main/suppliers_with_moq.csv")

lanes = pd.read_csv("/Users/deepjyotibhattacharjee/Developer/optimization_accelerator/optimization_data-main/lanes.csv")

# test_data/customers.csv
# /Users/deepjyotibhattacharjee/Developer/optimization_accelerator/test_data/customers.csv

# -------------------------------------------------
# Build model_def exactly like UI would
# -------------------------------------------------

model_def = {
    "datasets": {
        "suppliers": suppliers.to_dict(orient="records"),
        "customers": customers.to_dict(orient="records"),
        "lanes": lanes.to_dict(orient="records"),
    },
    "sets": {
        "suppliers": suppliers["supplier_id"].unique().tolist(),
        "customers": customers["customer_id"].unique().tolist(),
    },
    "parameters": {
        "ship_cost": {
            (row["supplier_id"], row["customer_id"]): row["ship_cost"]
            for _, row in lanes.iterrows()
        },
        "capacity": {
            row["supplier_id"]: row["capacity"]
            for _, row in suppliers.iterrows()
        },
        "demand": {
            row["customer_id"]: row["demand"]
            for _, row in customers.iterrows()
        }
    },
    "variables": [
        {
            "name": "x",
            "index": ["suppliers", "customers"],
            "type": "Continuous",
            "filter": {
                "dataset": "lanes",
                "column": "allowed",
                "value": 1
            }
        }
    ],
    "objective":
        "sum(ship_cost[i,j] * x[i,j] for i in suppliers for j in customers)",

    "constraints": [
    "sum(x[i,j] for j in customers) <= capacity[i] for i in suppliers",
    "sum(x[i,j] for i in suppliers) >= demand[j] for j in customers",
    "x[i,j] >= 10 * y[i,j] for i in suppliers for j in customers",
    "x[i,j] <= capacity[i] * y[i,j] for i in suppliers for j in customers"
]
}

# -------------------------------------------------
# Solve
# -------------------------------------------------

result = solve_model(model_def)

print("\n====================================")
print("REAL DATA RESULT")
print("Objective:", result["objective"])
print("====================================")

for var, values in result["solution"].items():
    print("\nVariable:", var)
    for k, v in values.items():
        if v > 0:
            print(k, "=", v)
