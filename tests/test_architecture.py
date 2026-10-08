import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"


def _assigns_state(node: ast.AST) -> bool:
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets.extend(node.targets)
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets.append(node.target)

    return any(
        isinstance(target, ast.Attribute) and target.attr == "state"
        for target in targets
    )


def test_only_confirm_and_cancel_assign_existing_reservation_state():
    state_writers = set()
    for source_file in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        module = source_file.relative_to(SOURCE_ROOT).as_posix()
        state_writers.update(
            (module, function.name)
            for function in ast.walk(tree)
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any(_assigns_state(statement) for statement in ast.walk(function))
        )

    assert state_writers == {
        ("main.py", "confirm_reservation"),
        ("main.py", "cancel_reservation"),
    }
