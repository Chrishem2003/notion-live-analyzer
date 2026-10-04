"""Phase 15 controlled model-comparison laboratory.

Compares advisory adapters against a frozen, human-labelled dataset without
mutating live observations or workflow state. Metrics are reproducible and
model/version/dataset bound. Results are evidence for human review only.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib, json, math, time, uuid
from typing import Any, Protocol
from nema_agora.evaluation import SUPPORTED_CATEGORIES, validate_advisory_output

class ComparisonAdapter(Protocol):
    provider: str
    model_version: str
    def analyse(self, record: dict[str, Any]) -> dict[str, Any]: ...

@dataclass(frozen=True)
class FrozenCase:
    case_id: str
    record: dict[str, Any]
    expected_category: str
    expected_duplicate: bool
    expected_summary_faithful: bool | None = None
    slice_name: str = "all"
    def __post_init__(self) -> None:
        if not self.case_id.strip(): raise ValueError("case_id is required")
        if self.expected_category not in SUPPORTED_CATEGORIES: raise ValueError("Unsupported expected category")
        if self.record.get("case_id") != self.case_id: raise ValueError("record.case_id must match case_id")
        if not isinstance(self.expected_duplicate, bool): raise ValueError("expected_duplicate must be boolean")

@dataclass(frozen=True)
class DatasetManifest:
    dataset_version: str
    frozen_at: str
    cases: int
    case_ids: tuple[str, ...]
    manifest_hash: str
    source: str = "human-annotated"
    def to_dict(self) -> dict[str, Any]: return asdict(self)

def freeze_dataset(cases: list[FrozenCase], dataset_version: str, *, frozen_at: str | None = None) -> DatasetManifest:
    version = dataset_version.strip()[:80]
    if not version: raise ValueError("dataset_version is required")
    if not cases: raise ValueError("Cannot freeze an empty dataset")
    ids = sorted(c.case_id for c in cases)
    if len(ids) != len(set(ids)): raise ValueError("Duplicate case IDs are not allowed")
    payload = json.dumps(
        [{"case_id": c.case_id, "expected_category": c.expected_category,
          "expected_duplicate": c.expected_duplicate,
          "expected_summary_faithful": c.expected_summary_faithful,
          "slice_name": c.slice_name} for c in sorted(cases, key=lambda x: x.case_id)],
        sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return DatasetManifest(version, frozen_at or datetime.now().astimezone().isoformat(timespec="seconds"),
                           len(cases), tuple(ids), hashlib.sha256(payload.encode()).hexdigest())

@dataclass(frozen=True)
class ComparisonMetrics:
    adapter: str
    provider: str
    model_version: str
    cases: int
    successful: int
    failures: int
    error_rate: float
    category_accuracy: float
    category_macro_precision: float
    category_macro_recall: float
    category_macro_f1: float
    duplicate_precision: float
    duplicate_recall: float
    duplicate_f1: float
    duplicate_false_positives: int
    duplicate_false_negatives: int
    summary_faithfulness: float | None
    mean_latency_ms: float
    confidence_brier: float | None
    confidence_cases: int
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class ComparisonResult:
    run_id: str
    created_at: str
    dataset: DatasetManifest
    adapters: tuple[ComparisonMetrics, ...]
    case_results: tuple[dict[str, Any], ...]
    slice_results: tuple[dict[str, Any], ...]
    model_disagreement: tuple[dict[str, Any], ...]
    regression: tuple[dict[str, Any], ...]
    readiness: str
    safety_notice: str
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["dataset"] = self.dataset.to_dict()
        d["adapters"] = [x.to_dict() for x in self.adapters]
        return d

def _ratio(n: float, d: float) -> float: return n / d if d else 0.0

def _category_metrics(rows: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    usable = [r for r in rows if r["predicted_category"] in SUPPORTED_CATEGORIES]
    accuracy = _ratio(sum(r["predicted_category"] == r["expected_category"] for r in usable), len(usable))
    ps, rs, fs = [], [], []
    for category in SUPPORTED_CATEGORIES:
        tp = sum(r["predicted_category"] == category and r["expected_category"] == category for r in usable)
        fp = sum(r["predicted_category"] == category and r["expected_category"] != category for r in usable)
        fn = sum(r["predicted_category"] != category and r["expected_category"] == category for r in usable)
        p, rec = _ratio(tp, tp+fp), _ratio(tp, tp+fn)
        ps.append(p); rs.append(rec); fs.append(_ratio(2*p*rec, p+rec))
    return accuracy, sum(ps)/len(ps), sum(rs)/len(rs), sum(fs)/len(fs)

def _duplicate_metrics(rows: list[dict[str, Any]]) -> tuple[float, float, float, int, int]:
    usable = [r for r in rows if isinstance(r["predicted_duplicate"], bool)]
    tp = sum(r["predicted_duplicate"] and r["expected_duplicate"] for r in usable)
    fp = sum(r["predicted_duplicate"] and not r["expected_duplicate"] for r in usable)
    fn = sum((not r["predicted_duplicate"]) and r["expected_duplicate"] for r in usable)
    p, rec = _ratio(tp, tp+fp), _ratio(tp, tp+fn)
    return p, rec, _ratio(2*p*rec, p+rec), fp, fn

def _confidence(output: dict[str, Any]) -> float | None:
    v = output.get("confidence")
    if isinstance(v, bool): return None
    try: v = float(v)
    except (TypeError, ValueError): return None
    return v if 0.0 <= v <= 1.0 and math.isfinite(v) else None

def _metrics(name: str, provider: str, version: str, rows: list[dict[str, Any]]) -> ComparisonMetrics:
    good = [r for r in rows if r["status"] == "OK"]
    acc, mp, mr, mf1 = _category_metrics(good)
    dp, dr, df1, fp, fn = _duplicate_metrics(good)
    faith = [r["expected_summary_faithful"] for r in good if r["expected_summary_faithful"] is not None]
    conf = [r for r in good if r["confidence"] is not None and r["predicted_category"] is not None]
    brier = _ratio(sum((r["confidence"] - (1.0 if r["predicted_category"] == r["expected_category"] else 0.0))**2 for r in conf), len(conf)) if conf else None
    return ComparisonMetrics(name, provider, version, len(rows), len(good), len(rows)-len(good),
        _ratio(len(rows)-len(good), len(rows)), acc, mp, mr, mf1, dp, dr, df1, fp, fn,
        _ratio(sum(faith), len(faith)) if faith else None, _ratio(sum(r["latency_ms"] for r in rows), len(rows)),
        brier, len(conf))

def compare_models(cases: list[FrozenCase], adapters: dict[str, ComparisonAdapter], *,
                   dataset: DatasetManifest, baseline_adapter: str | None = None) -> ComparisonResult:
    if dataset.cases != len(cases) or tuple(sorted(c.case_id for c in cases)) != dataset.case_ids:
        raise ValueError("Cases do not match the frozen dataset manifest")
    if not adapters: raise ValueError("At least one adapter is required")
    by_adapter: dict[str, list[dict[str, Any]]] = {}
    by_slice: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for name, adapter in adapters.items():
        provider = str(getattr(adapter, "provider", name)).strip()[:80] or name
        version = str(getattr(adapter, "model_version", "unknown")).strip()[:120] or "unknown"
        rows = []
        for case in cases:
            start = time.perf_counter(); status, output, error = "OK", None, ""
            try:
                output = adapter.analyse(dict(case.record))
                if not isinstance(output, dict): raise ValueError("Adapter output must be an object")
                errors = validate_advisory_output(output)
                if errors: raise ValueError("; ".join(errors))
                if output.get("source_case_id") != case.case_id: raise ValueError("source_case_id must match evaluation case")
            except Exception as exc:
                status, error = "ERROR", str(exc)[:500]
            latency = (time.perf_counter()-start)*1000.0
            suggestions = output.get("category_suggestions") if output else []
            predicted_category = output.get("predicted_category") if output else None
            if predicted_category not in SUPPORTED_CATEGORIES and isinstance(suggestions, list) and suggestions and isinstance(suggestions[0], dict):
                c = suggestions[0].get("category"); predicted_category = c if c in SUPPORTED_CATEGORIES else None
            candidates = output.get("duplicate_candidates") if output else []
            predicted_duplicate = bool(candidates) if isinstance(candidates, list) else None
            row = {"adapter":name,"provider":provider,"model_version":version,"case_id":case.case_id,
                   "slice":case.slice_name,"status":status,"error":error,"latency_ms":latency,
                   "expected_category":case.expected_category,"predicted_category":predicted_category,
                   "expected_duplicate":case.expected_duplicate,"predicted_duplicate":predicted_duplicate,
                   "expected_summary_faithful":case.expected_summary_faithful,"confidence":_confidence(output or {})}
            rows.append(row); by_slice.setdefault((name, case.slice_name), []).append(row)
        by_adapter[name] = rows
    metrics = tuple(_metrics(n, str(getattr(adapters[n],"provider",n))[:80],
                             str(getattr(adapters[n],"model_version","unknown"))[:120], rows)
                    for n, rows in by_adapter.items())
    slices = tuple({"adapter":n,"slice":s,**_metrics(n,rows[0]["provider"],rows[0]["model_version"],rows).to_dict()}
                   for (n,s),rows in sorted(by_slice.items()))
    disagreements = []
    names = sorted(by_adapter)
    if len(names) >= 2:
        for case in cases:
            rows = {n: next(r for r in by_adapter[n] if r["case_id"] == case.case_id) for n in names}
            cats = {n:r["predicted_category"] for n,r in rows.items()}
            dups = {n:r["predicted_duplicate"] for n,r in rows.items()}
            if len(set(v for v in cats.values() if v is not None)) > 1: disagreements.append({"case_id":case.case_id,"type":"category","predictions":cats})
            if len(set(v for v in dups.values() if v is not None)) > 1: disagreements.append({"case_id":case.case_id,"type":"duplicate","predictions":dups})
    regression = []
    if baseline_adapter in by_adapter:
        base = next(m for m in metrics if m.adapter == baseline_adapter)
        for m in metrics:
            if m.adapter == baseline_adapter: continue
            regression.append({"adapter":m.adapter,"baseline":baseline_adapter,
                "category_accuracy_delta":m.category_accuracy-base.category_accuracy,
                "category_macro_f1_delta":m.category_macro_f1-base.category_macro_f1,
                "duplicate_f1_delta":m.duplicate_f1-base.duplicate_f1,
                "error_rate_delta":m.error_rate-base.error_rate,
                "mean_latency_ms_delta":m.mean_latency_ms-base.mean_latency_ms})
    ready = len(cases) >= 25 and all(m.failures == 0 and m.category_accuracy >= .80 and m.duplicate_f1 >= .80 for m in metrics)
    return ComparisonResult(
        f"CMP-{uuid.uuid4().hex[:10].upper()}", datetime.now().astimezone().isoformat(timespec="seconds"),
        dataset, metrics, tuple(r for rows in by_adapter.values() for r in rows), slices,
        tuple(disagreements), tuple(regression), "READY_FOR_REVIEW" if ready else "NOT_READY",
        "Model comparison is measurement evidence only. It does not establish environmental truth, regulatory status, enforcement priority, or permission to deploy an AI model. All outputs remain advisory and require human review.")

def serialise_comparison(result: ComparisonResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
