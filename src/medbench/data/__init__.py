"""RuMedBench data layer: public API used by all other specs (contracts/cli.md)."""

from medbench.data.config import DataConfig, default_config, load_config
from medbench.data.errors import (
    ChecksumError,
    DataError,
    DataNotFoundError,
    LeakageError,
    RoleUnavailableError,
    SchemaError,
)
from medbench.data.fingerprint import fingerprint
from medbench.data.loaders import load_split, read_jsonl
from medbench.data.roles import ROLE_TABLE, check_leakage, get_role
from medbench.data.schemas import (
    ClassifExample,
    DaNetExample,
    Example,
    NERExample,
    NLIExample,
    Role,
    SourceSplit,
    TaskName,
    TestExample,
)

__all__ = [
    "ChecksumError",
    "ClassifExample",
    "DaNetExample",
    "DataConfig",
    "DataError",
    "DataNotFoundError",
    "Example",
    "LeakageError",
    "NERExample",
    "NLIExample",
    "ROLE_TABLE",
    "Role",
    "RoleUnavailableError",
    "SchemaError",
    "SourceSplit",
    "TaskName",
    "TestExample",
    "check_leakage",
    "default_config",
    "fingerprint",
    "get_role",
    "load_config",
    "load_split",
    "read_jsonl",
]
