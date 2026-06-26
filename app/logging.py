from collections.abc import Mapping, Sequence
from typing import Any
import re

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule


class TerminalLogger:
    SENSITIVE_VALUE_PATTERN = re.compile(
        r"(?i)(access[_-]?token|refresh[_-]?token|client[_-]?secret|"
        r"authorization|api[_-]?key|password|secret|database_url)"
        r"(['\"]?\s*[:=]\s*['\"]?)[^'\",\s}]+"
    )
    AUTH_HEADER_PATTERN = re.compile(
        r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)"
        r"(?:bearer|zoho-oauthtoken)\s+[^'\",\s}]+"
    )
    DATABASE_URL_PATTERN = re.compile(r"postgresql(?:\+\w+)?://[^\s]+", re.IGNORECASE)
    QUERY_SECRET_PATTERN = re.compile(
        r"(?i)([?&](?:access_token|refresh_token|client_secret|client_id|"
        r"api_key|password|token|secret)=)[^&\s]+"
    )

    def __init__(self) -> None:
        self.console = Console()

    def info(self, message: str) -> None:
        self.console.print(f"[bold cyan]INFO[/bold cyan] {self._sanitize(message)}")

    def ok(self, message: str) -> None:
        self.console.print(f"[bold green]OK[/bold green] {self._sanitize(message)}")

    def warn(self, message: str) -> None:
        self.console.print(f"[bold yellow]WARN[/bold yellow] {self._sanitize(message)}")

    def error(self, message: str) -> None:
        self.console.print(f"[bold red]ERROR[/bold red] {self._sanitize(message)}")

    def step(self, message: str) -> None:
        self.console.print(f"[bold blue]STEP[/bold blue] {self._sanitize(message)}")

    def bloque_inicio(self, title: str) -> None:
        self.console.print(
            Panel.fit(
                f"[bold cyan]{self._sanitize(title)}[/bold cyan]",
                border_style="cyan",
            )
        )

    def bloque_fin(self, title: str = "Fin") -> None:
        self.console.print(Rule(f"[bold cyan]{self._sanitize(title)}[/bold cyan]"))

    def subbloque_inicio(self, title: str) -> None:
        self.console.print(f"\n[bold magenta]▶ {self._sanitize(title)}[/bold magenta]")

    def subbloque_fin(self, title: str = "Subproceso finalizado") -> None:
        self.console.print(f"[dim magenta]✓ {self._sanitize(title)}[/dim magenta]\n")

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

        table = Table(
            title=self._sanitize(title), header_style="bold cyan", show_lines=False
        )

        for column_name in visible_columns:
            table.add_column(self._sanitize(str(column_name)), overflow="fold")

        for row_data in visible_rows:
            table.add_row(
                *(
                    self._stringify(row_data.get(column_name))
                    for column_name in visible_columns
                )
            )

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

                if isinstance(item, Sequence) and not isinstance(
                    item, (str, bytes, bytearray)
                ):
                    rows.append(
                        {
                            f"column_{column_index + 1}": value
                            for column_index, value in enumerate(item)
                        }
                    )
                    continue

                rows.append({"value": item, "row": index})

            return rows

        return [{"value": data}]

    def _normalize_mapping(self, data: Mapping[Any, Any]) -> dict[str, Any]:
        return {str(key): value for key, value in data.items()}

    def _stringify(self, value: Any) -> str:
        if value is None:
            return "-"

        return self._sanitize(str(value))

    def _sanitize(self, message: str) -> str:
        sanitized = self.AUTH_HEADER_PATTERN.sub(r"\1<redacted>", message)
        sanitized = self.SENSITIVE_VALUE_PATTERN.sub(r"\1\2<redacted>", sanitized)
        sanitized = self.DATABASE_URL_PATTERN.sub("postgresql://<redacted>", sanitized)
        return self.QUERY_SECRET_PATTERN.sub(r"\1<redacted>", sanitized)


log = TerminalLogger()
