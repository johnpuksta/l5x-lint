from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.errors import E008
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def e008_aoi_circular(
    _routine: Routine, symbols: SymbolTable, _loc: Location,
) -> list[Diagnostic]:
    if not symbols.aoi_list:
        return []

    graph: dict[str, list[str]] = {}
    for aoi in symbols.aoi_list:
        graph[aoi.name] = []

    result: list[Diagnostic] = []
    visited: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        if node in path:
            cycle = path[path.index(node):] + [node]
            result.append(
                Diagnostic(
                    code=E008.code,
                    severity=E008.severity,
                    location=Location(program="", routine=""),
                    message=E008(chain=cycle).message,
                )
            )
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor)
        path.pop()

    for aoi_name in graph:
        dfs(aoi_name)

    return result
