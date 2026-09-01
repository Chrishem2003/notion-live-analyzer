import ast
import operator


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression):

    if not expression.strip():
        raise ValueError("Expression cannot be empty.")

    tree = ast.parse(expression, mode="eval")

    def evaluate(node):

        if isinstance(node, ast.Constant):

            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError("Only numeric values are allowed.")

        if isinstance(node, ast.BinOp):

            operation = OPERATORS.get(type(node.op))

            if operation is None:
                raise ValueError("Operator is not allowed.")

            return operation(
                evaluate(node.left),
                evaluate(node.right),
            )

        if isinstance(node, ast.UnaryOp):

            operation = OPERATORS.get(type(node.op))

            if operation is None:
                raise ValueError("Unary operator is not allowed.")

            return operation(
                evaluate(node.operand)
            )

        raise ValueError("Unsupported expression.")

    return evaluate(tree.body)
