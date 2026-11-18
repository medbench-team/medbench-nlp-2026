"""Score predictions of one task on a labelled role (FR-001, FR-003, FR-004)."""

from medbench.data import DataConfig, Role, TaskName, get_role
from medbench.eval.errors import EvalUnavailableError
from medbench.eval.metrics import TaskMetrics, accuracy, hit_at_3, ner_f1, ner_token_accuracy
from medbench.eval.predictions import Prediction, validate_predictions

SCORABLE_ROLES = (Role.TUNE, Role.FINAL)


def metrics_from_pairs(task: TaskName | str, gold: list, pred: list) -> TaskMetrics:
    """Metrics from aligned gold/pred lists (gold: labels or tag sequences; pred: as in preds.jsonl)."""
    task = TaskName(task)
    if task in (TaskName.TOP3, TaskName.SYMPTOM_REC):
        return TaskMetrics(acc=accuracy(gold, [p[0] for p in pred]), hit3=hit_at_3(gold, pred))
    if task is TaskName.NER:
        return TaskMetrics(acc=ner_token_accuracy(gold, pred), f1=ner_f1(gold, pred))
    if task in (TaskName.NLI, TaskName.DANET):
        return TaskMetrics(acc=accuracy(gold, pred))
    raise EvalUnavailableError(f"{task}: локальная оценка невозможна — меток нет, только сабмит на medbench.ru.")


def score(
    task: TaskName | str, predictions: list[Prediction], role: Role | str, config: DataConfig | None = None
) -> TaskMetrics:
    task, role = TaskName(task), Role(role)
    if task is TaskName.TEST:
        raise EvalUnavailableError("RuMedTest: размеченных данных нет — качество только сабмитом на medbench.ru.")
    if role not in SCORABLE_ROLES:
        raise EvalUnavailableError(f"Роль {role} не оценивается локально: используйте tune (подбор) или final.")
    by_id = validate_predictions(task, role, predictions, config)
    examples = get_role(task, role, config)
    gold = [list(e.tags) if task is TaskName.NER else e.label for e in examples]
    pred = [by_id[e.id].prediction for e in examples]
    return metrics_from_pairs(task, gold, pred)
