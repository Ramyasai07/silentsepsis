# Deep Learning Methodology and Audit

## Scope and boundary

This note is intentionally limited to the deep-learning work in the AI research area. It reflects the current scripts and artifacts already present in the repository and does not modify the teammate-owned classical ML workflow or backend integration work.

Evidence for the canonical pipeline is in:
- [ai/scripts/create_sequences.py](../scripts/create_sequences.py)
- [ai/scripts/prepare_lstm_storage.py](../scripts/prepare_lstm_storage.py)
- [ai/scripts/train_lstm.py](../scripts/train_lstm.py)
- [ai/scripts/train_lstm_experiment3.py](../scripts/train_lstm_experiment3.py)
- [ai/scripts/train_lstm_experiment4.py](../scripts/train_lstm_experiment4.py)
- [ai/data/sequences/sequence_metadata.json](../data/sequences/sequence_metadata.json)

## 1. Task definition

The target definition is the early sepsis prediction task already represented by the PhysioNet `SepsisLabel` semantics. The preprocessing pipeline establishes patient-level onset and sets `target = 1` once the first positive label is reached; earlier rows remain negative. There is no additional 6-hour shift applied beyond the official label semantics that the pipeline uses.

This is consistent with the project’s earlier preprocessing contract and the canonical target logic described in the AI scripts.

## 2. Data contract and leakage-safe preprocessing

The deep-learning pipeline uses patient-aware, leakage-safe preprocessing before sequence generation.

Key properties:
- Patients are split at the patient level, not at the row level.
- Sequence windows only use contiguous ICU time steps with `ICULOS` differences of exactly 1.
- Windows are generated per patient and cannot cross patient boundaries.
- The final split artifact contains three patient partitions: train, validation, and test.
- All sequence arrays are validated for shape, class labels, and missing or infinite values.

The canonical sequence metadata states:
- sequence length: 12
- feature count: 76
- train sequences: 780,162
- validation sequences: 165,389
- test sequences: 164,640

The sequence metadata also documents the temporal rule:
> A valid sequence uses 12 consecutive ICU time steps with ICULOS differences of exactly 1. Any window with a gap is skipped.

This is implemented in [ai/scripts/create_sequences.py](../scripts/create_sequences.py), which is the sequence-generation source of truth for the LSTM pipeline.

## 3. Model architecture and training setup

The baseline Experiment 2 script in [ai/scripts/train_lstm.py](../scripts/train_lstm.py) implements the following architecture:
- Input shape: `(sequence_length, feature_count)`
- LSTM layer: 64 units
- Dropout: 0.3
- Dense layer: 32 units with ReLU
- Output layer: sigmoid for binary classification
- Optimizer: Adam
- Loss: binary cross-entropy
- Early stopping on validation PR-AUC
- Model checkpoint on validation PR-AUC

This is the key baseline model and the saved artifact is [ai/models/lstm_best.keras](../models/lstm_best.keras).

## 4. What Experiment 2, 3, and 4 actually differ by

The three scripts share the same recurrent architecture and data contract. They are not different architectures in the sense of GRU vs LSTM;
 all three use the same LSTM structure.

### Experiment 2: normalized LSTM baseline
- File: [ai/scripts/train_lstm.py](../scripts/train_lstm.py)
- Behavior: train-only normalization, standard binary cross-entropy, class weight balancing via `calculate_class_weights()`
- Output artifact: [ai/models/lstm_best.keras](../models/lstm_best.keras)
- Evaluation artifact: [ai/models/lstm_evaluation.json](../models/lstm_evaluation.json)

### Experiment 3: moderated class-weight LSTM
- File: [ai/scripts/train_lstm_experiment3.py](../scripts/train_lstm_experiment3.py)
- Behavior: same LSTM model, same data, same normalization strategy, but a moderated class weight based on the ratio of negatives to positives
- Weight logic: `positive_weight = sqrt(negative_count / positive_count)` and `negative_weight = 1.0`
- Output artifact: [ai/models/lstm_experiment3_best.keras](../models/lstm_experiment3_best.keras)
- Evaluation artifact: [ai/models/lstm_experiment3_evaluation.json](../models/lstm_experiment3_evaluation.json)

### Experiment 4: focal-loss LSTM
- File: [ai/scripts/train_lstm_experiment4.py](../scripts/train_lstm_experiment4.py)
- Behavior: same LSTM architecture, same normalization pipeline, but the loss is replaced with a focal-loss implementation
- Parameters: alpha = 0.25, gamma = 2.0
- Output artifact: [ai/models/lstm_experiment4_best.keras](../models/lstm_experiment4_best.keras)
- Evaluation artifact: [ai/models/lstm_experiment4_evaluation.json](../models/lstm_experiment4_evaluation.json)

## 5. Actual evaluated metrics in the saved artifacts

The baseline model evaluation in [ai/models/lstm_evaluation.json](../models/lstm_evaluation.json) reports:
- Validation ROC-AUC: 0.7899
- Validation PR-AUC: 0.0817
- Test ROC-AUC: 0.7853
- Test PR-AUC: 0.0685
- Validation F1 at threshold 0.5: 0.0958
- Test F1 at threshold 0.5: 0.0919

The Experiment 3 evaluation in [ai/models/lstm_experiment3_evaluation.json](../models/lstm_experiment3_evaluation.json) reports:
- Validation ROC-AUC: 0.7808
- Validation PR-AUC: 0.0712
- Test ROC-AUC: 0.7701
- Test PR-AUC: 0.0626
- Validation F1: 0.1151
- Test F1: 0.1144

The Experiment 4 evaluation in [ai/models/lstm_experiment4_evaluation.json](../models/lstm_experiment4_evaluation.json) reports:
- Validation ROC-AUC: 0.7842
- Validation PR-AUC: 0.0810
- Test ROC-AUC: 0.7789
- Test PR-AUC: 0.0668
- Validation F1: 0.0
- Test F1: 0.0

These numbers show that the baseline Experiment 2 and the imbalanced-loss variants did not produce a strong clinically useful separation at the default threshold. The threshold analysis script later chooses a higher threshold to maximize precision/recall trade-offs for a particular operating point, which is a different objective than the raw model training objective.

## 6. Threshold analysis

The threshold analysis in [ai/scripts/analyze_lstm_thresholds.py](../scripts/analyze_lstm_thresholds.py) and the saved artifact [ai/models/lstm_threshold_analysis.json](../models/lstm_threshold_analysis.json) identify a selected validation threshold of 0.85.

The resulting test metrics at threshold 0.85 are:
- precision: 0.1012
- recall: 0.1839
- F1: 0.1305
- ROC-AUC: 0.7853
- PR-AUC: 0.0685

This operating point improves specificity, but it is still a low-precision and low-PR-AUC model by clinical standards. The analysis also confirms that the model’s threshold-independent discrimination remains modest.

## 7. Early-warning analysis

The early-warning analysis script is [ai/scripts/analyze_lstm_early_warning.py](../scripts/analyze_lstm_early_warning.py). The saved result [ai/models/lstm_early_warning_analysis.json](../models/lstm_early_warning_analysis.json) explicitly notes that exact patient-level lead time is not available from the current sequence artifacts because the saved data does not retain alignment metadata such as patient ID, target time step, or sequence position.

This is important because it prevents inventing a precise early-warning time estimate from the available generated arrays alone.

## 8. SHAP analysis

The SHAP scripts and outputs are present in the model directory:
- [ai/scripts/analyze_lstm_shap.py](../scripts/analyze_lstm_shap.py)
- [ai/scripts/analyze_lstm_shap_direction.py](../scripts/analyze_lstm_shap_direction.py)
- [ai/models/lstm_shap_direction_analysis.json](../models/lstm_shap_direction_analysis.json)
- [ai/models/lstm_shap_feature_importance.csv](../models/lstm_shap_feature_importance.csv)

The project-specific notes confirm the directional SHAP output shape is `(100, 12, 76)` and that the analysis has already been run for the existing model. This work is a read-only explainability pass on the saved LSTM model and does not change the training pipeline itself.

## 9. GRU status

The original deep-learning pipeline is LSTM-based. The first set of AI experiments in this repository — Experiment 2, Experiment 3, and Experiment 4 — all use the same LSTM architecture and differ in their imbalance-handling strategy rather than in recurrent architecture.

A comparable GRU experiment has now been added in [ai/scripts/train_gru.py](../scripts/train_gru.py). The GRU uses the same patient-aware sequence contract as the baseline LSTM:
- sequence length: 12
- feature count: 76
- same patient-level train/validation/test split
- same train-only normalization approach
- same class-imbalance strategy as the baseline LSTM
- random seed: 42

The GRU evaluation is saved in [ai/models/gru_evaluation.json](../models/gru_evaluation.json). The verified results are:
- Validation ROC-AUC: 0.8065886890318261
- Validation PR-AUC: 0.08628613480127315
- Validation recall: 0.7343010413379615
- Test ROC-AUC: 0.793085729771604
- Test PR-AUC: 0.0749627870487889
- Test recall: 0.717940414507772

This gives a fair architecture comparison against the original LSTM baseline without changing the underlying sequence contract or preprocessing assumptions. The GRU is therefore a valid architecture comparison, while the original LSTM experiments remain distinct as imbalance-handling variants rather than different recurrent architectures.

The repository does not contain a verified Bi-LSTM, Transformer, CNN-LSTM, or other recurrent architecture implementation unless a separate file outside the current audited pipeline is added later. Based on the current implementation, there is no verified Bi-LSTM or Transformer experiment in the active deep-learning code path.

## 10. Bottom line

The repository contains a coherent deep-learning pipeline with the following characteristics:
- patient-aware preprocessing
- leakage-safe sequence generation
- 12-step ICU sequence windows
- stable LSTM baseline
- LSTM imbalance-handling variants (Experiments 2–4)
- a comparable GRU architecture experiment using the same sequence contract and training setup
- threshold and SHAP analysis on saved artifacts

The raw deep-learning evidence shows that the original LSTM pipeline remains the baseline sequence model, while the newly added GRU is a fair architecture comparison using the same data contract, normalization, and imbalance assumptions. The GRU currently has stronger validation discrimination on the recorded metrics, with validation ROC-AUC 0.8066 and validation PR-AUC 0.0863, compared with the LSTM baseline validation ROC-AUC 0.7899 and validation PR-AUC 0.0817. However, the overall discrimination remains limited for a highly imbalanced early sepsis task, and the PR-AUC values remain modest. The current AI research artifacts therefore support a valid LSTM-versus-GRU comparison, but they do not show a clinically deployable final model.
