from pulp import LpProblem, LpMinimize, value
from backend.model_builder import build_variables
from backend.expression_parser import parse_expression
import pandas as pd


def solve_model(model_def):

    # -----------------------------
    # Reconstruct datasets
    # -----------------------------
    datasets = {
        name: pd.DataFrame(records)
        for name, records in model_def["datasets"].items()
    }
    model_def["datasets"] = datasets

    # -----------------------------
    # Reconstruct parameter tuple keys FIRST
    # -----------------------------
    def reconstruct_keys(param_dict):
        new_dict = {}
        for key, value in param_dict.items():
            if isinstance(key, str) and "|" in key:
                new_key = tuple(key.split("|"))
            else:
                new_key = key
            new_dict[new_key] = value
        return new_dict

    model_def["parameters"] = {
        name: reconstruct_keys(p)
        for name, p in model_def["parameters"].items()
    }

    # -----------------------------
    # Now build context
    # -----------------------------
    context = {}
    context.update(model_def["sets"])
    context.update(model_def["parameters"])
    context["__datasets__"] = model_def["datasets"]

    # -----------------------------
    # Build variables
    # -----------------------------
    build_variables(model_def, context)

    # -----------------------------
    # Build model
    # -----------------------------
    prob = LpProblem("Generic_MILP", LpMinimize)

    print("\n========== DEBUG ==========")
    print("OBJECTIVE STRING:", model_def["objective"])
    print("CONSTRAINTS:", model_def["constraints"])
    print("===========================\n")


    prob += parse_expression(model_def["objective"], context)

    # for cons in model_def["constraints"]:
    #     prob += parse_expression(cons, context)

    # -----------------------------
    # Add Constraints
    # -----------------------------
    for cons in model_def["constraints"]:

        cons = cons.strip()

        # Detect outer quantifier
        if " for " in cons:

            # Split only on LAST " for "
            expr_part, quant_part = cons.rsplit(" for ", 1)

            if " in " in quant_part:

                var_name, set_name = quant_part.split(" in ")

                var_name = var_name.strip()
                set_name = set_name.strip()

                iterable = context[set_name]

                for val in iterable:
                    local_ctx = context.copy()
                    local_ctx[var_name] = val
                    prob += parse_expression(expr_part.strip(), local_ctx)

            else:
                prob += parse_expression(cons, context)

        else:
            prob += parse_expression(cons, context)


    prob.solve()

    # -----------------------------
    # Extract solution
    # -----------------------------
    solution = {}
    for var in model_def["variables"]:
        name = var["name"]
        solution[name] = {
            str(k): v.varValue
            for k, v in context[name].items()
        }

    return {
        "objective": value(prob.objective),
        "solution": solution
    }
