import copy
from concurrent.futures import ProcessPoolExecutor
from backend.solver_engine import solve_model


def run_parallel(base_model, scenarios, workers=4):

    def run_one(scenario):
        model_copy = copy.deepcopy(base_model)

        for p, v in scenario["overrides"].items():
            model_copy["parameters"][p] = v

        result = solve_model(model_copy)

        return {
            "scenario": scenario["name"],
            "objective": result["objective"]
        }

    with ProcessPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(run_one, scenarios))
