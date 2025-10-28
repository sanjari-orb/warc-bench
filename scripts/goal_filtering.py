import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import argparse


def remove_similar_goals_by_url(
    df: pd.DataFrame, similarity_threshold: float = 0.99
) -> pd.DataFrame:
    """
    Remove goals that are too similar to each other within the same URL group.

    Args:
        df: DataFrame containing 'subtask_goal' and 'start_url' columns
        similarity_threshold: Threshold above which goals are considered too similar (0-1)

    Returns:
        DataFrame with similar goals removed
    """
    # Make a copy to avoid modifying the input
    result_df = df.copy()

    # Process each URL group separately
    keep_indices = []

    for url, group in result_df.groupby("start_url"):
        if len(group) <= 1:
            # If only one goal for this URL, keep it
            keep_indices.extend(group.index.tolist())
            continue

        # Get goals for this URL group
        goals = group["subtask_goal"].tolist()

        # Calculate TF-IDF vectors
        vectorizer = TfidfVectorizer().fit(goals)
        vectors = vectorizer.transform(goals)

        # Calculate cosine similarity matrix
        similarity_matrix = cosine_similarity(vectors)

        # Set diagonal to 0 to avoid self-comparison
        np.fill_diagonal(similarity_matrix, 0)

        # Track which goals to keep
        goals_to_keep = set()
        goals_to_remove = set()

        # For each goal
        for i in range(len(goals)):
            if i in goals_to_remove:
                continue

            # Find all goals similar to this one
            similar_indices = np.nonzero(similarity_matrix[i] > similarity_threshold)[0]

            if len(similar_indices) > 0:
                print("Found group of similar goals:")
                print(f"Goal {i}: {goals[i]}")
                for j in similar_indices:
                    print(f"Goal {j}: {goals[j]}")

                # Keep this goal
                goals_to_keep.add(i)
                # Mark similar goals for removal
                goals_to_remove.update(similar_indices)

        # Get indices of all goals in this group
        group_indices = group.index.tolist()

        # Add indices of goals to keep to the result
        for i in range(len(goals)):
            if i not in goals_to_remove or i in goals_to_keep:
                keep_indices.append(group_indices[i])

    # Return filtered DataFrame
    return result_df.loc[keep_indices].reset_index(drop=True)


# test remove_similar_goals_by_url
if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--source_file_path", "-s", type=str, required=True)
    args.add_argument("--output_file_path", "-o", type=str, required=True)
    args = args.parse_args()

    df = pd.read_csv(args.source_file_path)
    df = remove_similar_goals_by_url(df)
    df.to_csv(args.output_file_path, index=False)
