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

        if len(sets) == 2:

            if filter_def:
                df = datasets[filter_def["dataset"]]
                col = filter_def["column"]
                val = filter_def["value"]

                df = df[df[col] == val]

                domain_pairs = list(
                    zip(df[index_sets[0]], df[index_sets[1]])
                )
            else:
                domain_pairs = [
                    (i, j)
                    for i in sets[0]
                    for j in sets[1]
                ]

            context[name] = {
                (i, j): LpVariable(
                    f"{name}_{i}_{j}",
                    lowBound=low_bound,
                    cat=var_type
                )
                for (i, j) in domain_pairs
            }
