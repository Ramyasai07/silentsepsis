# SilentSepsis Deep Learning Comparison

## 1. Dataset

The deep-learning sequence pipeline uses the PhysioNet-derived processed dataset that was already validated and profiled under the AI research workflow. The sequence metadata and sequence arrays are generated from the processed train/validation/test CSVs in the AI workspace.

Source data contract:
- processed CSVs: ai/data/processed/train.csv, validation.csv, test.csv
- split manifest: ai/data/splits/patient_split_manifest.csv
- sequence metadata: ai/data/sequences/sequence_metadata.json

The canonical sequence metadata records:
- sequence length: 12
- number of features: 76
- train sequences: 780,162
- validation sequences: 165,389
- test sequences: 164,640

## 2. Target definition

The target is the patient-level early sepsis target defined by the preprocessing pipeline and the existing label logic. The project treats the official PhysioNet SepsisLabel semantics as the early-warning target, and the processed target is set to 1 once the patient reaches the first positive SepsisLabel event; earlier timesteps remain negative.

This is not a future-horizon prediction in the sense of shifting the target forward by 6 hours. The existing implementation does not add a separate horizon shift beyond the official target semantics already described in the preprocessing logic.

## 3. Patient-level split

The sequence pipeline uses patient-level splitting, not row-level splitting.

Manifest-based split counts (as recorded in the project documentation):
- train patients: 28,234
- validation patients: 6,048
- test patients: 6,054

Integrity checks in the sequence pipeline enforce that:
- a patient appears in only one split
- sequences are created per patient and never cross patient boundaries
- the same patient does not appear across multiple split arrays

## 4. Input features

The model input features are the 76 sequence features recorded in ai/data/sequences/sequence_metadata.json. The feature list includes raw clinical variables and missingness indicators, with the final input list excluding protected columns such as patient_id, ICULOS, target, and SepsisLabel.

The exact feature ordering is the preserved feature ordering from the processed dataset and sequence metadata. The sequence creation code ensures this ordering is retained when it writes each sequence window.

## 5. Sequence construction

The canonical sequence generator is ai/scripts/create_sequences.py.

Key properties:
- sequence length = 12
- valid sequence windows require ICULOS increments of exactly 1 within each patient
- windows with gaps are skipped
- windows are never constructed across patient boundaries
- no future information is used when building a window from a patient history
- NaN and Inf values are rejected during validation

The sequence tensors have shape:
- (samples, 12, 76)

## 6. Normalization

Normalization is handled by train-only statistics.

The training script computes the mean and standard deviation from the training split only, then applies the same normalization to validation and test data. This is confirmed in the LSTM training code and the saved normalization stats file.

The LSTM training pipeline saves the normalization stats to ai/models/lstm_normalization_stats.json.

## 7. LSTM architecture

The baseline and Experiment 3 / 4 LSTM scripts share the same recurrent architecture.

Exact LSTM architecture:
- input shape: (12, 76)
- recurrent layer: 1 LSTM layer
- hidden units: 64
- dropout: 0.3
- dense layer: 32 units, ReLU
- output layer: sigmoid
- optimizer: Adam
- learning rate: default Keras Adam learning rate (not explicitly overridden in code)
- batch size: 256
- max epochs: 20
- early stopping: enabled on validation PR-AUC, patience = 3, restore_best_weights = True
- checkpointing: enabled on validation PR-AUC, save_best_only = True
- random seed: 42

The LSTM model is implemented in ai/scripts/train_lstm.py.

## 8. GRU architecture

The comparable GRU experiment was added using the same data contract and sequence pipeline. It uses the same shape, same training split, same normalization, and same patient-level leakage-safe sequence generation.

Exact GRU architecture:
- input shape: (12, 76)
- recurrent layer: 1 GRU layer
- hidden units: 64
- dropout: 0.3
- dense layer: 32 units, ReLU
- output layer: sigmoid
- optimizer: Adam
- learning rate: default Keras Adam learning rate
- batch size: 256
- maximum epochs: 20
- early stopping: enabled on validation PR-AUC, patience = 3, restore_best_weights = True
- random seed: 42
- class weighting: same baseline class-weight strategy derived from training counts

This new experiment is implemented in ai/scripts/train_gru.py and its evaluation artifact is ai/models/gru_evaluation.json.

## 9. Training configuration

The common training setup is:
- same processed data
- same patient splits
- same sequence length and feature count
- same train-only normalization
- same validation/test split logic
- same threshold default of 0.5 for evaluation unless a separate threshold-analysis script is used
- same random seed = 42

Use of validation data:
- validation is used for model selection and early stopping
- test data is reserved for final reporting and is not used for hyperparameter selection

## 10. Class imbalance handling

The saved LSTM experiments differ by class-imbalance strategy, not by architecture:

- Baseline LSTM: binary cross-entropy with class weights derived from training counts
- Experiment 3: moderated class weighting
- Experiment 4: focal loss
- GRU: baseline class-weighted binary cross-entropy, matching the same imbalance treatment as the baseline LSTM for a comparable architecture test

The GRU comparison is therefore fair and uses the same data contract and class imbalance handling as the baseline LSTM, rather than introducing a different tuning setup.

## 11. Evaluation methodology

For all reported deep-learning metrics, the project uses the same held-out test set and evaluates on:
- ROC-AUC
- PR-AUC / Average Precision
- precision
- recall
- F1
- accuracy
- confusion matrix

The LSTM evaluation JSONs and the GRU evaluation JSON store the recorded metrics. This comparison uses the actual saved metrics rather than recalculating or inventing values.

## 12. LSTM results

The existing saved LSTM evaluation files are:
- ai/models/lstm_evaluation.json
- ai/models/lstm_experiment3_evaluation.json
- ai/models/lstm_experiment4_evaluation.json

The baseline LSTM test results at threshold 0.5:
- ROC-AUC: 0.7853207308793819
- PR-AUC: 0.0685216506371865
- precision: 0.04953896678034609
- recall: 0.635038860103627
- F1: 0.09190823237175731
- accuracy: 0.7646319241982508
- confusion matrix: [123928, 37624, 1127, 1961]

The saved Experiment 3 evaluation at threshold 0.5:
- ROC-AUC: 0.770123896327386
- PR-AUC: 0.06261411609903769
- precision: 0.10353866317169069
- recall: 0.12791450777202074
- F1: 0.114442995798928
- accuracy: 0.9628705053449952
- confusion matrix: [158132, 3420, 2693, 395]

The saved Experiment 4 evaluation at threshold 0.5:
- ROC-AUC: 0.7789106310786664
- PR-AUC: 0.06675199145344853
- precision: 0.0
- recall: 0.0
- F1: 0.0
- accuracy: 0.9812257045675413
- confusion matrix: [161549, 3, 3088, 0]

## 13. GRU results

The new GRU model was trained and evaluated with the same sequence contract as the LSTM baseline. The saved evaluation artifact is ai/models/gru_evaluation.json.

GRU test results at threshold 0.5:
- ROC-AUC: 0.793085729771604
- PR-AUC: 0.0749627870487889
- precision: 0.04841245578023322
- recall: 0.717940414507772
- F1: 0.09070823616054989
- accuracy: 0.7300291545189505
- confusion matrix: [117975, 43577, 871, 2217]

Validation results:
- ROC-AUC: 0.8065886890318261
- PR-AUC: 0.08628613480127315
- precision: 0.051673217418337664
- recall: 0.7343010413379615
- F1: 0.09655201029002945
- accuracy: 0.7366934923120643
- confusion matrix: [119514, 42706, 842, 2327]

## 14. LSTM vs GRU comparison table

| Model | Validation PR-AUC | Validation F1 | Validation Recall | Validation ROC-AUC | Test PR-AUC | Test F1 | Test Recall | Test ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LSTM baseline | 0.08169969176121819 | 0.09582257185508139 | 0.6380561691385295 | 0.7899421851099677 | 0.0685216506371865 | 0.09190823237175731 | 0.635038860103627 | 0.7853207308793819 |
| LSTM Experiment 3 | 0.0712386091310295 | 0.11511701454775458 | 0.11486273272325655 | 0.780792913402277 | 0.06261411609903769 | 0.114442995798928 | 0.12791450777202074 | 0.770123896327386 |
| LSTM Experiment 4 | 0.08095869134578478 | 0.0 | 0.0 | 0.7842010102491235 | 0.06675199145344853 | 0.0 | 0.0 | 0.7789106310786664 |
| GRU | 0.08628613480127315 | 0.09655201029002945 | 0.7343010413379615 | 0.8065886890318261 | 0.0749627870487889 | 0.09070823616054989 | 0.717940414507772 | 0.793085729771604 |

The GRU has the highest validation PR-AUC and the highest validation ROC-AUC. The GRU also has the highest validation recall. The trade-off is lower precision and more false positives than the baseline, but the validation discrimination is modestly stronger under the imbalanced problem setting.

## 15. Best model

Using validation PR-AUC as the primary model-selection metric for this imbalanced early sepsis task, the best model is the GRU.

Why:
- validation PR-AUC: GRU = 0.08628613480127315 > LSTM baseline = 0.08169969176121819
- validation ROC-AUC: GRU = 0.8065886890318261 > baseline = 0.7899421851099677
- validation recall: GRU = 0.7343010413379615 > baseline = 0.6380561691385295

This is the primary basis for selecting the GRU as the best-performing model under the current validation contract. Accuracy should not be used as the main decision criterion because the problem is highly imbalanced.

## 16. Early-warning analysis

The early-warning analysis remains limited by metadata availability.

The existing artifact ai/models/lstm_early_warning_analysis.json states:
- exact_patient_level_lead_time: NOT AVAILABLE FROM CURRENT SEQUENCE ARTIFACTS
- sequence_metadata_has_required_alignment: false

This means the sequence arrays and metadata do not provide sufficient patient/time alignment to compute an exact patient-level early-warning lead time without fabricating missing information.

## 17. Limitations

- Class imbalance remains severe.
- PR-AUC values remain low overall, which indicates limited discrimination even for the best-performing model.
- Threshold trade-offs are significant: raising the decision threshold improves precision but sharply reduces recall.
- The label definition is patient-level and does not imply a precise clinically validated lead-time target.
- Exact early-warning timing cannot be trusted without patient-level sequence alignment metadata.
- No GRU/Bi-LSTM comparison beyond the added GRU was introduced in this work.

## 18. Conclusion

The deep-learning work confirms that the same patient-aware sequence pipeline can be evaluated under a comparable GRU architecture with the same data contract, and the GRU is slightly stronger on validation PR-AUC and recall than the existing LSTM baseline. However, the overall discrimination remains limited under the highly imbalanced sepsis setting; the LSTM and GRU models still do not deliver a clinically strong operating point based on the recorded metrics. The current AI work is therefore a valid research comparison and baseline, not a production-ready clinical model.
