from fastapi import FastAPI
from backend.solver_engine import solve_model

app = FastAPI()

@app.post("/solve")
def solve(payload: dict):
    return solve_model(payload)
