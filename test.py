from pulp import *

def solve_universal(df, config):
    prob = LpProblem("Weighted_Optimization", LpMinimize)
    
    idx = df.index
    # x[i] represents the FLOW (actual units shipped)
    x = LpVariable.dicts("flow", idx, lowBound=0, cat='Continuous')
    
    # y[o] handles the Activation of an Origin (for MOQ)
    origins = df[config['origin_id']].unique()
    y = LpVariable.dicts("active", origins, cat='Binary')

    # THE FIX: We must multiply the Unit Cost by the Flow Variable
    # Total Cost = Sum ( (Unit_Cost + Shipping) * Quantity )
    prob += lpSum([df.loc[i, config['goal_col']] * x[i] for i in idx])

    # Constraint: Total flow into a destination must equal its Requirement (Demand)
    for d in df[config['dest_id']].unique():
        d_idx = df[df[config['dest_id']] == d].index
        prob += lpSum([x[i] for i in d_idx]) == float(df.loc[d_idx[0], config['requirement']])

    # Constraint: Total flow out of an origin must be between MOQ and Capacity
    for o in origins:
        o_idx = df[df[config['origin_id']] == o].index
        total_flow = lpSum([x[i] for i in o_idx])
        prob += total_flow <= float(df.loc[o_idx[0], config['upper_limit']]) * y[o]
        prob += total_flow >= float(df.loc[o_idx[0], config['lower_limit']]) * y[o]

    prob.solve(PULP_CBC_CMD(msg=0))
    return {str(i): x[i].varValue for i in idx if x[i].varValue > 0} if LpStatus[prob.status] == 'Optimal' else {"error": "Infeasible"}