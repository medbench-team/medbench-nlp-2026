"""Data-layer exceptions with human-readable (Russian) messages."""

from pathlib import Path


class DataError(Exception):
    """Base class for all data errors."""


class DataNotFoundError(DataError):
    def __init__(self, path: Path | str):
        super().__init__(
            f"Файл данных не найден: {path}. Скачайте данные: `uv run medbench data download`."
        )
        self.path = Path(path)


class ChecksumError(DataError):
    def __init__(self, path: Path | str, expected: str, actual: str):
        super().__init__(f"sha256 не совпадает для {path}: ожидалось {expected}, получено {actual}.")
        self.path, self.expected, self.actual = Path(path), expected, actual


class RowCountError(DataError):
    def __init__(self, path: Path | str, expected: int, actual: int):
        super().__init__(f"Неверное число строк в {path}: ожидалось {expected}, получено {actual}.")


class SchemaError(DataError):
    def __init__(self, task: str, file: Path | str, line: int, detail: str):
        super().__init__(f"{task}: ошибка в {file}, строка {line}: {detail}")
        self.task, self.file, self.line, self.detail = task, Path(file), line, detail


class RoleUnavailableError(DataError):
    """The requested role does not exist for this task (e.g. labelled data for RuMedTest)."""


class LeakageError(DataError):
    """Examples of the `final` role leak into `train` or `tune`."""
