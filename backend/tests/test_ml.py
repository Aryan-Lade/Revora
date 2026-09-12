from app.ml import model as ml_model
from app.services import context as context_service


def test_ml_model_train_generates_metrics():
    model, scaler, metrics = ml_model._train_and_save()
    assert model is not None
    assert scaler is not None
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "roc_auc" in metrics

    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0


def test_ml_predict_recovery_probability_for_case(db, case):
    ctx = context_service.build(db, case)
    prob = ml_model.predict_recovery_probability(ctx)
    assert isinstance(prob, float)
    assert 0.05 <= prob <= 0.99
