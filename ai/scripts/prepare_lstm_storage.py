from pathlib import Path
import gc
import os

import numpy as np


SEQUENCE_ROOT = Path(__file__).resolve().parents[1] / "data" / "sequences"

EXPECTED_SHAPES = {
    "train": (780162, 12, 76),
    "validation": (165389, 12, 76),
    "test": (164640, 12, 76),
}

SPLITS = ["train", "validation", "test"]


def validate_split(split_name: str, X: np.ndarray, y: np.ndarray) -> None:
    if X.ndim != 3:
        raise ValueError(f"{split_name}: X must be 3D, got shape {X.shape}.")

    expected_shape = EXPECTED_SHAPES[split_name]
    if X.shape != expected_shape:
        raise ValueError(f"{split_name}: expected X shape {expected_shape}, got {X.shape}.")

    if X.shape[0] != y.size:
        raise ValueError(
            f"{split_name}: X and y sample counts do not match: X={X.shape[0]}, y={y.size}."
        )

    if np.isnan(X).any():
        raise ValueError(f"{split_name}: X contains NaN values.")

    if np.isinf(X).any():
        raise ValueError(f"{split_name}: X contains Inf values.")

    unique_labels = np.unique(y)
    if not np.all(np.isin(unique_labels, [0, 1])):
        raise ValueError(f"{split_name}: y contains values outside {0, 1}: {unique_labels}.")


def verify_mappable(path: Path) -> bool:
    loaded = np.load(path, mmap_mode="r")
    return isinstance(loaded, np.memmap)


def convert_split(split_name: str) -> None:
    npz_path = SEQUENCE_ROOT / f"{split_name}_sequences.npz"
    x_out = SEQUENCE_ROOT / f"{split_name}_X.npy"
    y_out = SEQUENCE_ROOT / f"{split_name}_y.npy"

    if not npz_path.exists():
        raise FileNotFoundError(f"Missing NPZ file: {npz_path}")

    with np.load(npz_path) as data:
        X = np.asarray(data["X"])
        y = np.asarray(data["y"]).reshape(-1)

    validate_split(split_name, X, y)

    temp_x = SEQUENCE_ROOT / f"{split_name}_X.tmp.npy"
    temp_y = SEQUENCE_ROOT / f"{split_name}_y.tmp.npy"

    np.save(temp_x, X, allow_pickle=False)
    np.save(temp_y, y, allow_pickle=False)

    x_temp_loaded = np.load(temp_x, mmap_mode="r")
    y_temp_loaded = np.load(temp_y, mmap_mode="r")
    if x_temp_loaded.shape != X.shape:
        raise ValueError(f"{split_name}: temporary X shape mismatch after save: {x_temp_loaded.shape}.")
    if y_temp_loaded.shape != y.shape:
        raise ValueError(f"{split_name}: temporary y shape mismatch after save: {y_temp_loaded.shape}.")

    del x_temp_loaded
    del y_temp_loaded
    gc.collect()

    os.replace(temp_x, x_out)
    os.replace(temp_y, y_out)

    x_final = np.load(x_out, mmap_mode="r")
    y_final = np.load(y_out, mmap_mode="r")

    x_mappable = isinstance(x_final, np.memmap)
    y_mappable = isinstance(y_final, np.memmap)

    print(f"{split_name.upper()}:")
    print(f"  X shape: {x_final.shape}")
    print(f"  y shape: {y_final.shape}")
    print(f"  X memory-mappable: {'YES' if x_mappable else 'NO'}")
    print(f"  y memory-mappable: {'YES' if y_mappable else 'NO'}")

    del x_final
    del y_final
    gc.collect()

    del X, y


def main() -> None:
    print("STORAGE CONVERSION")

    for split_name in SPLITS:
        convert_split(split_name)
        print()

    for split_name in SPLITS:
        npz_path = SEQUENCE_ROOT / f"{split_name}_sequences.npz"
        if not npz_path.exists():
            raise FileNotFoundError(f"Original NPZ missing after conversion: {npz_path}")

    print("FINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
