from fastapi import FastAPI
from backend.solver_engine import solve_model
from backend.scenario_runner import run_parallel
from backend.db import init_db, save_model, save_result

app = FastAPI()
init_db()


@app.post("/solve")
def solve(payload: dict):

    result = solve_model(payload)

    if payload.get("save"):
        model_id = save_model(payload["name"], payload)
        save_result(model_id, result["objective"], result["solution"])

    return result


@app.post("/run_scenarios")
def scenarios(payload: dict):
    return run_parallel(
        payload["model"],
        payload["scenarios"],
        payload.get("workers", 4)
    )
