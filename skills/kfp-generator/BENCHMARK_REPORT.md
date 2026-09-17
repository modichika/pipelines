
| Suite | Domain | BEFORE Compile | AFTER Compile | AFTER Latency | Failure Resolved |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Iris Classification** | Classical ML / Tabular | ❌ FAIL | ✅ PASS (0.4s) | 0.4s | Container boundary import isolation & typed artifacts |
| **Customer Churn** | Tabular ETL & XGBoost | ✅ PASS | ✅ PASS (0.4s) | 0.4s | Missing runtime packages (xgboost) & artifact path creation |
| **MNIST Classification** | Vision / Deep Learning | ❌ FAIL | ✅ PASS (0.4s) | 0.4s | Legacy KFP v1 ContainerOp syntax hallucination |
| **Time-Series Forecasting** | Telemetry / Regressor | ✅ PASS | ✅ PASS (0.4s) | 0.4s | Numpy metric type serialization & typed Output[Metrics] |
| **Image Anomaly Detection** | Vision / Embeddings | ✅ PASS | ✅ PASS (0.4s) | 0.4s | Missing vision libraries (Pillow) & directory artifact linkage |

### Summary Statistics
* **Total Pipelines Evaluated**: 5
* **Static Compile Pass Rate**: BEFORE = 3/5 (60%) ➔ AFTER = 5/5 (100%)
* **Identified Bottleneck**: Cold-start container pip builds (e.g. MNIST at ~21 mins vs lightweight tasks at ~2 mins).
