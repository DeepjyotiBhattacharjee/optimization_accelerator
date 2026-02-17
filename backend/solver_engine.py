from pulp import LpProblem, LpMinimize, value
from backend.model_builder import build_variables
from backend.expression_parser import parse_expression


def solve_model(model_def):

    context = {}
    context.update(model_def["sets"])
    context.update(model_def["parameters"])
    context["__datasets__"] = model_def["datasets"]

    build_variables(model_def, context)

    prob = LpProblem("Generic_MILP", LpMinimize)

    prob += parse_expression(model_def["objective"], context)

    for cons in model_def["constraints"]:
        prob += parse_expression(cons, context)

    prob.solve()

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
