import numpy as np

from app.ml.features import FAILURE_RECOVERABILITY, METHOD_RECOVERABILITY, build_features

WEIGHTS = np.array([-1.35, 0.55, 2.05, -1.15, 0.75, -0.85, -1.95, -0.95, 3.05, 0.85, 0.65, 1.25])
BIAS = -4.81
SAMPLES = 6000


def latent(vector: np.ndarray) -> np.ndarray:
    return vector @ WEIGHTS + BIAS


def generate(samples: int = SAMPLES, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    failures = list(FAILURE_RECOVERABILITY)
    methods = list(METHOD_RECOVERABILITY)
    rows = []
    for _ in range(samples):
        successful = int(rng.integers(0, 40))
        failed = int(rng.integers(0, 12))
        rows.append(
            build_features(
                amount=float(rng.gamma(2.0, 3200)),
                lifetime_value=float(rng.gamma(2.4, 32000)),
                successful_payments=successful,
                failed_payments=failed,
                recoveries_succeeded=int(rng.integers(0, 5)),
                recoveries_failed=int(rng.integers(0, 4)),
                attempt_number=int(rng.integers(1, 5)),
                days_since_failure=float(rng.exponential(1.8)),
                failure_type=failures[int(rng.integers(0, len(failures)))],
                method=methods[int(rng.integers(0, len(methods)))],
                subscription_age_days=float(rng.integers(10, 900)),
                engagement=float(rng.beta(4, 3)),
            )
        )
    features = np.array(rows, dtype=float)
    probability = 1 / (1 + np.exp(-latent(features)))
    labels = (rng.random(samples) < probability).astype(int)
    return features, labels
