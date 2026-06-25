from collections.abc import Mapping, Sequence
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table


class TerminalLogger:
    def __init__(self) -> None:
        self.console = Console()

    def info(self, message: str) -> None:
        self.console.print(f"[bold cyan]INFO[/bold cyan] {message}")

    def ok(self, message: str) -> None:
        self.console.print(f"[bold green]OK[/bold green] {message}")

    def warn(self, message: str) -> None:
        self.console.print(f"[bold yellow]WARN[/bold yellow] {message}")

    def error(self, message: str) -> None:
        self.console.print(f"[bold red]ERROR[/bold red] {message}")

    def step(self, message: str) -> None:
        self.console.print(f"[bold blue]STEP[/bold blue] {message}")

    def bloque_inicio(self, title: str) -> None:
        self.console.print(
            Panel.fit(
                f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
            )
        )

    def bloque_fin(self, title: str = "Fin") -> None:
        self.console.print(Rule(f"[bold cyan]{title}[/bold cyan]"))

    def subbloque_inicio(self, title: str) -> None:
        self.console.print(f"\n[bold magenta]▶ {title}[/bold magenta]")

    def subbloque_fin(self, title: str = "Subproceso finalizado") -> None:
        self.console.print(f"[dim magenta]✓ {title}[/dim magenta]\n")

    def table(
        self,
        data: Any,
        columns: int,
        rows: int,
        title: str = "Data Preview",
    ) -> None:
        normalized_rows = self._normalize_rows(data)

        if not normalized_rows:
            self.warn(f"{title}: no hay datos para mostrar")
            return

        visible_rows = normalized_rows[: max(rows, 0)]
        visible_columns = list(normalized_rows[0].keys())[: max(columns, 0)]

        if not visible_columns:
            self.warn(f"{title}: no hay columnas para mostrar")
            return

        table = Table(title=title, header_style="bold cyan", show_lines=False)

        for column_name in visible_columns:
            table.add_column(str(column_name), overflow="fold")

        for row_data in visible_rows:
            table.add_row(*(self._stringify(row_data.get(column_name)) for column_name in visible_columns))

        total_rows = len(normalized_rows)
        total_columns = len(normalized_rows[0])
        table.caption = (
            f"Mostrando {len(visible_rows)} de {total_rows} filas y "
            f"{len(visible_columns)} de {total_columns} columnas"
        )

        self.console.print(table)

    def _normalize_rows(self, data: Any) -> list[dict[str, Any]]:
        if hasattr(data, "to_dict"):
            dataframe_rows = data.to_dict(orient="records")
            if isinstance(dataframe_rows, list):
                return [self._normalize_mapping(row) for row in dataframe_rows]

        if isinstance(data, Mapping):
            return [self._normalize_mapping(data)]

        if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
            rows: list[dict[str, Any]] = []
            for index, item in enumerate(data):
                if isinstance(item, Mapping):
                    rows.append(self._normalize_mapping(item))
                    continue

                if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
                    rows.append({f"column_{column_index + 1}": value for column_index, value in enumerate(item)})
                    continue

                rows.append({"value": item, "row": index})

            return rows

        return [{"value": data}]

    def _normalize_mapping(self, data: Mapping[Any, Any]) -> dict[str, Any]:
        return {str(key): value for key, value in data.items()}

    def _stringify(self, value: Any) -> str:
        if value is None:
            return "-"

        return str(value)


log = TerminalLogger()
