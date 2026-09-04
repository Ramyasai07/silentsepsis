import json
from pathlib import Path

import numpy as np
import pandas as pd
from tensorflow import keras

REPO_ROOT = Path(__file__).resolve().parents[1]
SEQUENCE_ROOT = REPO_ROOT / "data" / "sequences"
SPLIT_MANIFEST = REPO_ROOT / "data" / "splits" / "patient_split_manifest.csv"
SEQUENCE_METADATA = SEQUENCE_ROOT / "sequence_metadata.json"


def test_sequence_metadata_contract():
    with SEQUENCE_METADATA.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    assert metadata["sequence_length"] == 12
    assert metadata["number_of_features"] == 76
    assert len(metadata["feature_names"]) == 76


def test_split_manifest_integrity():
    manifest = pd.read_csv(SPLIT_MANIFEST)
    assert not manifest.empty
    assert manifest["patient_id"].is_unique
    assert set(manifest["split"]).issubset({"train", "validation", "test"})


def test_sequence_arrays_are_well_formed():
    for split_name in ["train", "validation", "test"]:
        X = np.load(
            SEQUENCE_ROOT / f"{split_name}_X.npy", mmap_mode="r", allow_pickle=False
        )
        y = np.load(
            SEQUENCE_ROOT / f"{split_name}_y.npy", mmap_mode="r", allow_pickle=False
        )

        assert X.ndim == 3
        assert X.shape[1] == 12
        assert X.shape[2] == 76
        assert X.shape[0] == y.shape[0]
        assert np.isfinite(X).all()
        assert set(np.unique(y)).issubset({0, 1})


def test_lstm_model_forward_pass():
    model = keras.Sequential(
        [
            keras.layers.Input(shape=(12, 76)),
            keras.layers.LSTM(64),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    x = np.random.default_rng(42).normal(size=(2, 12, 76)).astype(np.float32)
    y = model(x)
    assert y.shape == (2, 1)
    assert np.all((y >= 0.0) & (y <= 1.0))


def test_gru_model_forward_pass():
    model = keras.Sequential(
        [
            keras.layers.Input(shape=(12, 76)),
            keras.layers.GRU(64),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    x = np.random.default_rng(42).normal(size=(2, 12, 76)).astype(np.float32)
    y = model(x)
    assert y.shape == (2, 1)
    assert np.all((y >= 0.0) & (y <= 1.0))
