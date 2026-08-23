# LSTM Experiment Comparison

## 1. Objective

The LSTM experiments were performed to evaluate the same patient-aware sequence pipeline under different class-imbalance handling strategies for early sepsis prediction. The code and artifacts show a single recurrent architecture applied to the same processed sequence data, with the main experimental variables being the loss or weighting strategy rather than a different neural-network design.

## 2. Common LSTM Architecture

The common architecture is consistent across the baseline Experiment 2, Experiment 3, and Experiment 4 scripts:

- Sequence length: 12
- Input features: 76
- Number of LSTM layers: 1
- Hidden units: 64
- Dropout: 0.3 after the LSTM layer
- Dense head: 32 units with ReLU, followed by 1 sigmoid output unit
- Optimizer: Adam
- Learning rate: not explicitly set in the code; the scripts use the default Keras Adam learning rate
- Batch size: 256
- Maximum epochs: 20
- Early stopping: enabled using validation PR-AUC, patience = 3, restore_best_weights = True
- Checkpointing: enabled using validation PR-AUC, save_best_only = True
- Random seed: 42
- Training normalization: train-only statistics, using the mean and standard deviation computed from the training split
- Class weighting / loss configuration:
  - Baseline: binary cross-entropy with class weights derived from the training set counts
  - Experiment 3: moderated class weighting using a positive weight of sqrt(negative_count / positive_count)
  - Experiment 4: focal loss with alpha = 0.25 and gamma = 2.0

This comes directly from the scripts in [../scripts/train_lstm.py](../scripts/train_lstm.py), [../scripts/train_lstm_experiment3.py](../scripts/train_lstm_experiment3.py), [../scripts/train_lstm_experiment4.py](../scripts/train_lstm_experiment4.py), and the sequence metadata in [../data/sequences/sequence_metadata.json](../data/sequences/sequence_metadata.json).

## 3. Experimental Variations

The actual code does not define separate architectures. All three experiments use the same LSTM architecture and the same sequence data contract; the substantive change is the imbalance handling strategy.

### Baseline experiment

- Script: [../scripts/train_lstm.py](../scripts/train_lstm.py)
- Name in code: EXPERIMENT 2: NORMALIZED LSTM
- Configuration: train-only normalization, binary cross-entropy, class-weight balancing from training counts
- Evaluation file: [../models/lstm_evaluation.json](../models/lstm_evaluation.json)

### Experiment 3

- Script: [../scripts/train_lstm_experiment3.py](../scripts/train_lstm_experiment3.py)
- Name in code: EXPERIMENT 3: MODERATED CLASS WEIGHT LSTM
- Change: same architecture and normalization, but with moderated class weighting instead of the baseline class-weight scheme
- Evaluation file: [../models/lstm_experiment3_evaluation.json](../models/lstm_experiment3_evaluation.json)

### Experiment 4

- Script: [../scripts/train_lstm_experiment4.py](../scripts/train_lstm_experiment4.py)
- Name in code: EXPERIMENT 4: FOCAL LOSS LSTM
- Change: same architecture and normalization, but with focal loss instead of binary cross-entropy
- Evaluation file: [../models/lstm_experiment4_evaluation.json](../models/lstm_experiment4_evaluation.json)

The important point is that these are not different LSTM architectures. They are the same LSTM architecture with different imbalance-handling configurations: baseline class-weighted binary cross entropy, moderated class weighting, and focal loss.

## 4. Results

The comparison below uses only metrics that are actually recorded in the saved evaluation JSON files. The JSON files store confusion matrices in the order: [TN, FP, FN, TP].

| Experiment | Split | Threshold | ROC-AUC | PR-AUC / Average Precision | Precision | Recall | F1 | Accuracy | Specificity | Confusion matrix [TN, FP, FN, TP] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline Experiment 2 | Validation | 0.5 | 0.7899421851099677 | 0.08169969176121819 | 0.05180099400522621 | 0.6380561691385295 | 0.09582257185508139 | 0.7692772796256099 | Not reported | [125208, 37012, 1147, 2022] |
| Baseline Experiment 2 | Test | 0.5 | 0.7853207308793819 | 0.0685216506371865 | 0.04953896678034609 | 0.635038860103627 | 0.09190823237175731 | 0.7646319241982508 | Not reported | [123928, 37624, 1127, 1961] |
| Experiment 3 | Validation | 0.5 | 0.780792913402277 | 0.0712386091310295 | 0.11537242472266244 | 0.11486273272325655 | 0.11511701454775458 | 0.9661646179612913 | Not reported | [159429, 2791, 2805, 364] |
| Experiment 3 | Test | 0.5 | 0.770123896327386 | 0.06261411609903769 | 0.10353866317169069 | 0.12791450777202074 | 0.114442995798928 | 0.9628705053449952 | Not reported | [158132, 3420, 2693, 395] |
| Experiment 4 | Validation | 0.5 | 0.7842010102491235 | 0.08095869134578478 | 0.0 | 0.0 | 0.0 | 0.9808270199348204 | Not reported | [162218, 2, 3169, 0] |
| Experiment 4 | Test | 0.5 | 0.7789106310786664 | 0.06675199145344853 | 0.0 | 0.0 | 0.0 | 0.9812257045675413 | Not reported | [161549, 3, 3088, 0] |

Notes:
- Specificity is not reported in any of the three evaluation JSON files, so it is marked as Not reported.
- Validation and test metrics are reported, but training metrics are not recorded in the JSON files.
- The threshold used in these evaluation files is 0.5 unless a separate threshold analysis is applied.

## 5. Threshold Analysis

The threshold-analysis artifact is [../models/lstm_threshold_analysis.json](../models/lstm_threshold_analysis.json), and the analysis script is [../scripts/analyze_lstm_thresholds.py](../scripts/analyze_lstm_thresholds.py).

### Selected threshold

The artifact records a selected threshold of 0.85.

### Why it differs from 0.5

The threshold-analysis script evaluates a grid of thresholds from 0.10 to 0.90 and selects the threshold based on validation F1, with recall as the tie-breaker when F1 values are tied. This is the actual logic implemented in [../scripts/analyze_lstm_thresholds.py](../scripts/analyze_lstm_thresholds.py), and the saved JSON records the selected result of 0.85.

### Actual threshold results

From [../models/lstm_threshold_analysis.json](../models/lstm_threshold_analysis.json):

- Selected threshold: 0.85
- Validation metrics at 0.85:
  - precision: 0.115959844294202
  - recall: 0.1786052382455033
  - F1: 0.14062111801242236
  - accuracy: 0.9581713415039694
- Test metrics at 0.85:
  - precision: 0.10115761353517365
  - recall: 0.18393782383419688
  - F1: 0.13052970240147077
  - accuracy: 0.9540391156462585
  - ROC-AUC: 0.7853207308793819
  - PR-AUC: 0.0685216506371865

### Did the higher threshold improve the operating point?

The higher threshold improved specificity and reduced false positives, but it sharply reduced recall. Compared with the 0.5 threshold baseline on the same model, the threshold 0.85 trade-off is:

- Baseline at 0.5 on test:
  - precision: 0.04953896678034609
  - recall: 0.635038860103627
  - F1: 0.09190823237175731
- Selected threshold 0.85 on test:
  - precision: 0.10115761353517365
  - recall: 0.18393782383419688
  - F1: 0.13052970240147077

This means the higher threshold made the model more conservative and more precise, but much less sensitive. It did improve the practical operating point in the sense of reducing false positives, yet it still did not create strong classification performance overall. The model remains weakly discriminative at the reported PR-AUC and F1 levels.

## 6. Early-Warning Analysis

The early-warning analysis is in [../scripts/analyze_lstm_early_warning.py](../scripts/analyze_lstm_early_warning.py) and the saved result is [../models/lstm_early_warning_analysis.json](../models/lstm_early_warning_analysis.json).

### What it can establish

It can establish:
- probability distribution summaries for test sequences
- the positive and negative mean/median probabilities
- the count of predictions above 0.85
- threshold-specific test metrics for the final Experiment 2 model
- that sequence-level discrimination is limited on the current saved test set

The JSON explicitly records the tested probability distribution and threshold behavior.

### What it cannot establish

It cannot establish exact patient-level lead time from the existing sequence artifacts. The JSON explicitly states:

- exact_patient_level_lead_time: NOT AVAILABLE FROM CURRENT SEQUENCE ARTIFACTS
- reason: the current sequence artifacts and metadata do not include patient_id, start/end ICULOS, target timestep, or patient sequence position
- sequence_metadata_has_required_alignment: false

This limitation is important: without the sequence-to-patient and sequence-to-time alignment metadata, it is not possible to recover a valid patient-level early-warning lead time without inventing missing information. The current artifacts do not support that calculation.

## 7. Best LSTM Configuration

Using the actual evaluation JSON results at the default threshold of 0.5, the best-performing configuration is Experiment 3.

Why:
- Validation F1: Experiment 3 = 0.11511701454775458, higher than baseline = 0.09582257185508139 and Experiment 4 = 0.0
- Test F1: Experiment 3 = 0.114442995798928, higher than baseline = 0.09190823237175731 and Experiment 4 = 0.0
- Validation precision: Experiment 3 = 0.11537242472266244, higher than baseline = 0.05180099400522621
- Test precision: Experiment 3 = 0.10353866317169069, higher than baseline = 0.04953896678034609

Experiment 3 therefore delivers the strongest thresholded classification performance in the saved evaluation artifacts. It is not the best by ROC-AUC or PR-AUC, because the baseline Experiment 2 has slightly higher ROC-AUC and PR-AUC on the validation/test sets, but the classification metrics reported in the saved evaluation JSONs favor Experiment 3 at the reported threshold. Experiment 4 is the weakest configuration by a large margin, with zero positive detections at the 0.5 threshold.

## 8. Limitations

- Class imbalance is severe; the test set contains a positive rate of roughly 1.9% in the sequence-level early sepsis task.
- Discrimination remains limited. The best reported ROC-AUC is only around 0.79, and the PR-AUC values sit around 0.06 to 0.08, which is weak for a clinically important screening model.
- Threshold trade-offs are substantial. Raising the threshold from 0.5 to 0.85 improves precision and specificity but reduces recall sharply.
- The sequence artifacts do not include sufficient patient/time alignment metadata for exact patient-level lead-time estimation.
- No verified GRU or Bi-LSTM comparison is present in the current implementation.

## 9. Final Conclusion

The LSTM work establishes a reproducible patient-aware sequence pipeline, but the recorded evaluation evidence does not show a strong clinically deployable early sepsis model. The same architecture was reused across all three experiments, and the experimental variable was the imbalance-handling strategy: baseline class-weighted binary cross entropy, moderated class weighting, and focal loss. Based on the saved evaluation JSONs, Experiment 3 provides the strongest thresholded performance among the recorded experiments, while the baseline remains competitive on discrimination metrics and Experiment 4 performs poorly. The threshold and early-warning analyses also clarify the trade-offs: higher thresholds reduce false positives but significantly reduce recall, and the current artifacts cannot support exact patient-level lead-time estimation. The current implementation is a valid research baseline, not a final production-grade early-warning system.

## Summary of evidence used

- [../scripts/train_lstm.py](../scripts/train_lstm.py)
- [../scripts/train_lstm_experiment3.py](../scripts/train_lstm_experiment3.py)
- [../scripts/train_lstm_experiment4.py](../scripts/train_lstm_experiment4.py)
- [../scripts/analyze_lstm_thresholds.py](../scripts/analyze_lstm_thresholds.py)
- [../scripts/analyze_lstm_early_warning.py](../scripts/analyze_lstm_early_warning.py)
- [../models/lstm_evaluation.json](../models/lstm_evaluation.json)
- [../models/lstm_experiment3_evaluation.json](../models/lstm_experiment3_evaluation.json)
- [../models/lstm_experiment4_evaluation.json](../models/lstm_experiment4_evaluation.json)
- [../models/lstm_threshold_analysis.json](../models/lstm_threshold_analysis.json)
- [../models/lstm_early_warning_analysis.json](../models/lstm_early_warning_analysis.json)
- [../data/sequences/sequence_metadata.json](../data/sequences/sequence_metadata.json)

## Final statement on architecture and GRU

No verified GRU/Bi-LSTM experiment is present in the current implementation.
