"""Planning only: expected population arithmetic, no model calls."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def loaded():
    spec=importlib.util.spec_from_file_location(
        "learned_budget",ROOT/"scripts/plan_learned_full_matrix.py")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def test_full_candidate_count_tracks_declared_model_and_dataset_matrix():
    rows=loaded().build_budget()
    code=rows["code"]
    assert code["MBPP_train_completion_candidates"]==279360
    assert code["MBPP_evaluation_candidates"]==2016000
    assert code["HumanEvalPlus_candidates"]==157440
    assert sum(code["additional_transfer_candidates"].values())==542400
    assert code["total_code_completion_candidates"]==2995200
    assert rows["text_domains"]["math"]["eval_generation_candidates"]==168000
    assert rows["text_domains"]["qa"]["eval_generation_candidates"]==252672
