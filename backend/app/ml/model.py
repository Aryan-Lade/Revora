from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.ml.dataset import generate
from app.ml.features import FEATURE_NAMES

MODEL_NAME = "recovery_probability_logistic"
ARTIFACT = Path(__file__).parent / "artifacts" / "recovery_model.joblib"

_state: dict = {}


def train(samples: int | None = None) -> dict:
    features, labels = generate() if samples is None else generate(samples)
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=11, stratify=labels
    )
    estimator = LogisticRegression(max_iter=2000, C=1.5)
    estimator.fit(x_train, y_train)
    scores = estimator.predict_proba(x_test)[:, 1]
    positive_rate = float(y_train.mean())
    threshold = float(np.quantile(scores, 1 - positive_rate))
    predictions = (scores >= threshold).astype(int)
    importance = sorted(
        (
            {"feature": name, "weight": round(float(weight), 4)}
            for name, weight in zip(FEATURE_NAMES, estimator.coef_[0])
        ),
        key=lambda item: abs(item["weight"]),
        reverse=True,
    )
    metrics = {
        "model_name": MODEL_NAME,
        "training_samples": int(len(x_train)),
        "test_samples": int(len(x_test)),
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, scores)), 4),
        "positive_rate": round(positive_rate, 4),
        "threshold": round(threshold, 4),
        "feature_importance": importance,
        "dataset": "synthetic",
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"estimator": estimator, "metrics": metrics}, ARTIFACT)
    _state["estimator"] = estimator
    _state["metrics"] = metrics
    return metrics


def load() -> tuple[LogisticRegression, dict]:
    if "estimator" not in _state:
        if ARTIFACT.exists():
            bundle = joblib.load(ARTIFACT)
            _state["estimator"] = bundle["estimator"]
            _state["metrics"] = bundle["metrics"]
        else:
            train()
    return _state["estimator"], _state["metrics"]


def predict(vector: list[float]) -> float:
    estimator, _ = load()
    value = estimator.predict_proba(np.array([vector], dtype=float))[:, 1][0]
    return round(float(value), 4)


def metrics() -> dict:
    _, values = load()
    return values
