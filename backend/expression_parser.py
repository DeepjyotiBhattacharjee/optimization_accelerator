import ast
from pulp import lpSum


class LinearParser(ast.NodeVisitor):

    def __init__(self, context):
        self.context = context

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right

        raise ValueError("Unsupported operator")

    def visit_Compare(self, node):
        left = self.visit(node.left)
        right = self.visit(node.comparators[0])

        if isinstance(node.ops[0], ast.Eq):
            return left == right
        if isinstance(node.ops[0], ast.LtE):
            return left <= right
        if isinstance(node.ops[0], ast.GtE):
            return left >= right

        raise ValueError("Unsupported comparison")

    def visit_Call(self, node):
        if node.func.id != "sum":
            raise ValueError("Only sum() allowed")
        return self.handle_generator(node.args[0])

    def handle_generator(self, gen):

        def recursive_build(generators, local_ctx):
            if not generators:
                return LinearParser(local_ctx).visit(gen.elt)

            current = generators[0]
            target = current.target.id
            iterable = self.context[current.iter.id]

            results = []
            for val in iterable:
                new_ctx = local_ctx.copy()
                new_ctx[target] = val
                results.append(recursive_build(generators[1:], new_ctx))

            return lpSum(results)

        return recursive_build(gen.generators, self.context)

    def visit_Subscript(self, node):
        name = node.value.id

        if isinstance(node.slice, ast.Tuple):
            index = tuple(self.visit(e) for e in node.slice.elts)
        else:
            index = self.visit(node.slice)

        if isinstance(index, tuple):
            if index in self.context[name]:
                pass
            elif tuple(reversed(index)) in self.context[name]:
                index = tuple(reversed(index))
            else:
                raise KeyError(
                    f"Index {index} not found in {name}"
                )

        return self.context[name][index]

    def visit_Name(self, node):
        return self.context[node.id]

    def visit_Constant(self, node):
        return node.value


def parse_expression(expr, context):
    tree = ast.parse(expr, mode="eval")
    return LinearParser(context).visit(tree)
