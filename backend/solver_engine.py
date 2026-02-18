from pulp import LpProblem, LpMinimize, value
from backend.model_builder import build_variables
from backend.expression_parser import parse_expression
import pandas as pd


def solve_model(model_def):

    # ---------------------------------
    # Reconstruct datasets
    # ---------------------------------
    datasets = {
        name: pd.DataFrame(records)
        for name, records in model_def["datasets"].items()
    }
    model_def["datasets"] = datasets

    # ---------------------------------
    # Reconstruct parameter tuple keys
    # ---------------------------------
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

    # ---------------------------------
    # Build context
    # ---------------------------------
    context = {}
    context.update(model_def["sets"])
    context.update(model_def["parameters"])
    context["__datasets__"] = model_def["datasets"]

    # ---------------------------------
    # Build variables
    # ---------------------------------
    build_variables(model_def, context)

    # ---------------------------------
    # Build model
    # ---------------------------------
    prob = LpProblem("Generic_MILP", LpMinimize)

    # Objective
    prob += parse_expression(model_def["objective"], context)

    # ---------------------------------
    # Constraints (multi-quantifier)
    # ---------------------------------
    for cons in model_def["constraints"]:

        cons = cons.strip()
        parts = cons.split(" for ")

        if len(parts) > 1:

            expr_part = parts[0].strip()
            quantifiers = parts[1:]

            parsed_quantifiers = []
            for q in quantifiers:
                var_name, set_name = q.split(" in ")
                parsed_quantifiers.append(
                    (var_name.strip(), set_name.strip())
                )

            def expand(level, local_ctx):
                if level == len(parsed_quantifiers):
                    prob += parse_expression(expr_part, local_ctx)
                    return

                var_name, set_name = parsed_quantifiers[level]
                iterable = context[set_name]

                for val in iterable:
                    new_ctx = local_ctx.copy()
                    new_ctx[var_name] = val
                    expand(level + 1, new_ctx)

            expand(0, context)

        else:
            prob += parse_expression(cons, context)

    prob.solve()

    # ---------------------------------
    # Extract solution
    # ---------------------------------
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
