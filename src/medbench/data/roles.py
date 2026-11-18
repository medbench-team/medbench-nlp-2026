"""Split roles train / tune / final / submit with a leakage guard (FR-005, FR-006, FR-008, ADR-014)."""

from medbench.data.config import DataConfig, default_config
from medbench.data.errors import LeakageError, RoleUnavailableError
from medbench.data.fingerprint import fingerprint
from medbench.data.loaders import load_split
from medbench.data.schemas import Example, Role, TaskName

_CORE = {"train": "train", "tune": "dev", "final": "test", "submit": "private_test"}
_EXTENDED = {"train": "train", "tune": "dev", "final": "test"}

# Role → source split of the open repository (data-model.md, «Роли»). Site data never enters a role.
ROLE_TABLE: dict[str, dict[str, str]] = {
    TaskName.NLI: _CORE,
    TaskName.DANET: _CORE,
    TaskName.TEST: {"submit": "private_test"},
    TaskName.NER: _EXTENDED,
    TaskName.TOP3: _EXTENDED,
    TaskName.SYMPTOM_REC: _EXTENDED,
}


def _unavailable(task: TaskName, role: Role) -> RoleUnavailableError:
    if task is TaskName.TEST:
        return RoleUnavailableError(
            "RuMedTest: размеченных данных нет, доступна только роль submit "
            "(оценка — сабмитом на medbench.ru)."
        )
    return RoleUnavailableError(
        f"{task}: роль {role} недоступна — у задачи нет закрытого test (private_test), "
        f"доступны: {', '.join(ROLE_TABLE[task])}."
    )


def _final_fingerprints(task: TaskName, config: DataConfig) -> set[str]:
    return {fingerprint(e) for e in load_split(task, ROLE_TABLE[task]["final"], config)}


def _without_final(task: TaskName, role: Role, config: DataConfig) -> list[Example]:
    """train/tune minus rows duplicating a `final` example; the count must match known_overlaps."""
    examples = load_split(task, ROLE_TABLE[task][role], config)
    final = _final_fingerprints(task, config)
    kept = [e for e in examples if fingerprint(e) not in final]
    removed = len(examples) - len(kept)
    expected = config.known_overlaps.get(task, {}).get(role, 0)
    if removed != expected:
        raise LeakageError(
            f"{task}: {removed} строк(и) роли {role} совпадают с примерами роли final, "
            f"а в configs/data.yaml (known_overlaps) ожидается {expected}. "
            "Это новая утечка или изменение данных — разберитесь, прежде чем продолжать (принцип I)."
        )
    return kept


def check_leakage(task: TaskName | str, config: DataConfig | None = None) -> None:
    """Raise LeakageError unless train/tune overlap `final` exactly as declared in known_overlaps."""
    task, config = TaskName(task), config or default_config()
    for role in (Role.TRAIN, Role.TUNE):
        if role in ROLE_TABLE[task] and "final" in ROLE_TABLE[task]:
            _without_final(task, role, config)


def get_role(task: TaskName | str, role: Role | str, config: DataConfig | None = None) -> list[Example]:
    """Examples of `task` for `role`. Never touches the network.

    train/tune exclude the known duplicates of `final` (ADR-014); final and submit are the
    official splits, unchanged.
    """
    task, role, config = TaskName(task), Role(role), config or default_config()
    if role not in ROLE_TABLE[task]:
        raise _unavailable(task, role)
    if role in (Role.TRAIN, Role.TUNE) and "final" in ROLE_TABLE[task]:
        return _without_final(task, role, config)
    if role is Role.FINAL:
        check_leakage(task, config)
    return load_split(task, ROLE_TABLE[task][role], config)
