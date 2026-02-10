import numpy as np
from sklearn.metrics import mean_absolute_error, r2_score


def rmsle(y_true, y_pred):
    """
    Root Mean Squared Logarithmic Error
    """
    y_true = np.maximum(y_true, 0)
    y_pred = np.maximum(y_pred, 0)
    return np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2))


def compute_metrics(y_true, y_pred):
    return {
        "rmsle": rmsle(y_true, y_pred),
        "mae": mean_absolute_error(y_true, y_pred),
        "r2": r2_score(y_true, y_pred),
    }
