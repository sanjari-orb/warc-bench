import numpy as np
import scipy.stats as stats


def confidence_interval(data, confidence=0.95):
    """
    Calculate the confidence interval for a given set of success rates.

    Parameters:
        data (list or array): List of success rates from multiple runs.
        confidence (float): Confidence level (default: 0.95 for 95% CI).

    Returns:
        tuple: (lower_bound, upper_bound, std_dev)
    """
    n = len(data)
    if n < 2:
        raise ValueError(
            "At least two data points are required to calculate a confidence interval."
        )

    mean = np.mean(data)
    std_dev = np.std(data, ddof=1)  # Sample standard deviation

    t_critical = stats.t.ppf(
        (1 + confidence) / 2, df=n - 1
    )  # t-score for confidence interval

    margin_of_error = t_critical * (std_dev / np.sqrt(n))

    return mean - margin_of_error, mean + margin_of_error, std_dev
