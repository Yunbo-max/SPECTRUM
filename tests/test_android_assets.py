import json

import pytest

from improving.android.assets import MODEL_ID, MODEL_REVISION, file_sha256, resolve_checkpoint


def acquired_model(tmp_path):
    checkpoint = tmp_path / "model"
    checkpoint.mkdir()
    (checkpoint / "config.json").write_text("{}")
    (checkpoint / "model.safetensors").write_bytes(b"original")
    receipt = tmp_path / "assets.json"
    receipt.write_text(json.dumps({"model": {
        "repo_id": MODEL_ID, "revision": MODEL_REVISION,
        "checkpoint": str(checkpoint),
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": file_sha256(p)}
                  for p in checkpoint.iterdir()},
    }}))
    return checkpoint, {"model": {}, "assets_receipt": str(receipt)}


def test_acquired_model_hashes_match_before_resolution(tmp_path):
    checkpoint, config = acquired_model(tmp_path)
    assert resolve_checkpoint(config) == str(checkpoint)


def test_same_size_weight_change_is_rejected_before_model_load(tmp_path):
    checkpoint, config = acquired_model(tmp_path)
    (checkpoint / "model.safetensors").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        resolve_checkpoint(config)
