from pulp import LpVariable


def build_variables(model_def, context):

    datasets = context["__datasets__"]

    for var_def in model_def["variables"]:

        name = var_def["name"]
        index_sets = var_def.get("index", [])
        var_type = var_def.get("type", "Continuous")
        low_bound = var_def.get("low_bound", None)
        filter_def = var_def.get("filter", None)

        sets = [context[s] for s in index_sets]

        # Bounds
        if var_type == "Binary":
            lowBound = 0
            upBound = 1
            cat = "Binary"
        elif var_type == "Integer":
            lowBound = 0 if low_bound is None else low_bound
            upBound = None
            cat = "Integer"
        else:
            lowBound = 0 if low_bound is None else low_bound
            upBound = None
            cat = "Continuous"

        # 1D
        if len(sets) == 1:
            context[name] = {
                i: LpVariable(
                    f"{name}_{i}",
                    lowBound=lowBound,
                    upBound=upBound,
                    cat=cat
                )
                for i in sets[0]
            }

        # 2D
        elif len(sets) == 2:

            if filter_def:
                df = datasets[filter_def["dataset"]]
                col = filter_def["column"]
                val = filter_def["value"]
                df = df[df[col] == val]

                index_columns = df.columns[:2]
                domain_pairs = list(zip(*(df[c] for c in index_columns)))
            else:
                domain_pairs = [
                    (i, j)
                    for i in sets[0]
                    for j in sets[1]
                ]

            context[name] = {
                (i, j): LpVariable(
                    f"{name}_{i}_{j}",
                    lowBound=lowBound,
                    upBound=upBound,
                    cat=cat
                )
                for (i, j) in domain_pairs
            }
