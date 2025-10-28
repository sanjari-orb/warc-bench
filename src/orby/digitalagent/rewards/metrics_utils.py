import pandas as pd
from typing import Any, Dict, Optional, Union, List, Tuple


def calculate_metrics(
    results: Optional[pd.DataFrame],
    gt_col: str = "gt_success",
    pred_col: str = "llm_pred_success",
    run_id: str = "test",
):
    """
    Calculate confusion matrix, F1 score, recall, precision, and accuracy
    for two Boolean columns in a pd.DataFrame.

    Args:
        results (Dict or pd.DataFrame): DataFrame containing the columns.
        gt_col (str): Ground truth column name (BooleanType).
        pred_col (str): Predicted response column name (BooleanType).

    Returns:
        dict: Dictionary containing the confusion matrix and metrics (F1, recall, precision, accuracy).
    """
    results = (
        pd.DataFrame(results) if not isinstance(results, pd.DataFrame) else results
    )
    # Confusion matrix components
    tp = results[results[gt_col] & results[pred_col]].shape[0]
    tn = results[(~results[gt_col]) & (~results[pred_col])].shape[0]
    fp = results[(~results[gt_col]) & results[pred_col]].shape[0]
    fn = results[(results[gt_col]) & (~results[pred_col])].shape[0]

    # Derived metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "Run": run_id,
        "TP,TN,FP,FN": [tp, tn, fp, fn],
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "f1_score": round(f1, 4),
    }
