#!/usr/bin/env python3
"""
Script to analyze task types in the CSV file and create visualizations.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re
import os

def parse_task_types(task_types_str):
    """
    Parse the task types string and return a list of individual task types.
    Handles comma-separated values and strips whitespace.
    """
    if pd.isna(task_types_str) or task_types_str == '':
        return []
    
    # Split by comma and clean up each task type
    task_types = [task_type.strip() for task_type in str(task_types_str).split(',')]
    return [task_type for task_type in task_types if task_type]

def analyze_task_types(csv_file_path):
    """
    Analyze task types from the CSV file and return statistics.
    """
    print(f"Reading CSV file: {csv_file_path}")
    
    # Read the CSV file
    df = pd.read_csv(csv_file_path)
    
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Check if 'task types' column exists
    if 'task types' not in df.columns:
        print("Error: 'task types' column not found in CSV file")
        return None
    
    # Parse all task types and create mapping
    all_task_types = []
    task_type_to_ids = {}
    
    for idx, row in df.iterrows():
        task_id = row.get('task id', idx)  # Use task id column if available, otherwise use index
        task_types = parse_task_types(row['task types'])
        all_task_types.extend(task_types)
        
        # Create mapping from task types to task IDs
        for task_type in task_types:
            if task_type not in task_type_to_ids:
                task_type_to_ids[task_type] = []
            task_type_to_ids[task_type].append(task_id)
    
    # Count occurrences
    task_type_counts = Counter(all_task_types)

    
    print(f"\nTotal individual task type instances: {len(all_task_types)}")
    print(f"Unique task types: {len(task_type_counts)}")
    
    return task_type_counts, df, task_type_to_ids

def create_visualizations(task_type_counts, output_dir='.'):
    """
    Create various visualizations of the task type distribution.
    """
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Sort task types by count for better visualization
    sorted_types = sorted(task_type_counts.items(), key=lambda x: x[1], reverse=True)
    task_types, counts = zip(*sorted_types)
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle('Task Type Distribution Analysis', fontsize=16, fontweight='bold')
    
    # 1. Horizontal bar chart (top 20)
    top_n = min(20, len(task_types))
    ax1.barh(range(top_n), counts[:top_n])
    ax1.set_yticks(range(top_n))
    ax1.set_yticklabels(task_types[:top_n], fontsize=10)
    ax1.set_xlabel('Count')
    ax1.set_title(f'Top {top_n} Task Types by Count')
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. Pie chart (top 10)
    top_10 = min(10, len(task_types))
    other_count = sum(counts[top_10:])
    
    pie_labels = list(task_types[:top_10])
    pie_counts = list(counts[:top_10])
    
    if other_count > 0:
        pie_labels.append('Others')
        pie_counts.append(other_count)
    
    ax2.pie(pie_counts, labels=pie_labels, autopct='%1.1f%%', startangle=90)
    ax2.set_title(f'Distribution of Top {top_10} Task Types')
    
    # 3. All task types bar chart
    ax3.bar(range(len(task_types)), counts)
    ax3.set_xlabel('Task Type Index')
    ax3.set_ylabel('Count')
    ax3.set_title('All Task Types Distribution')
    ax3.grid(axis='y', alpha=0.3)
    
    # Rotate x-axis labels for better readability
    ax3.set_xticks(range(0, len(task_types), max(1, len(task_types)//10)))
    ax3.set_xticklabels([task_types[i] for i in range(0, len(task_types), max(1, len(task_types)//10))], 
                        rotation=45, ha='right')
    
    # 4. Cumulative distribution
    cumulative_counts = []
    cumulative_sum = 0
    for count in counts:
        cumulative_sum += count
        cumulative_counts.append(cumulative_sum)
    
    total_count = sum(counts)
    cumulative_percentages = [c/total_count * 100 for c in cumulative_counts]
    
    ax4.plot(range(len(task_types)), cumulative_percentages, marker='o', markersize=3)
    ax4.set_xlabel('Task Type Index (sorted by count)')
    ax4.set_ylabel('Cumulative Percentage')
    ax4.set_title('Cumulative Distribution of Task Types')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=80, color='r', linestyle='--', alpha=0.7, label='80% threshold')
    ax4.axhline(y=90, color='orange', linestyle='--', alpha=0.7, label='90% threshold')
    ax4.legend()
    
    plt.tight_layout()
    
    # Save the plot
    plot_path = os.path.join(output_dir, 'task_types_distribution.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {plot_path}")
    
    return fig

def print_task_type_mapping(task_type_to_ids, task_type_counts, max_display=20):
    """
    Print a table showing the mapping between task types and task IDs.
    """
    print("\n" + "="*80)
    print("TASK TYPE TO TASK ID MAPPING")
    print("="*80)
    
    # Sort task types by count (most frequent first)
    sorted_types = sorted(task_type_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"{'Task Type':<35} {'Count':<6} {'Task IDs':<35}")
    print("-" * 80)
    
    for i, (task_type, count) in enumerate(sorted_types):
        if i >= max_display:
            remaining = len(sorted_types) - max_display
            print(f"... and {remaining} more task types")
            break
            
        task_ids = sorted(task_type_to_ids[task_type])
        
        # Format task IDs for display (show first few, then "...")
        if len(task_ids) <= 8:
            ids_str = ", ".join(map(str, task_ids))
        else:
            ids_str = ", ".join(map(str, task_ids[:5])) + f", ... (+{len(task_ids)-5} more)"
        
        print(f"{task_type:<35} {count:<6} {ids_str:<35}")
    
    print("\n" + "="*80)

def save_task_type_mapping(task_type_to_ids, task_type_counts, output_dir='.'):
    """
    Save the task type to task ID mapping to a CSV file.
    """
    mapping_path = os.path.join(output_dir, 'task_type_to_ids_mapping.csv')
    
    # Prepare data for CSV
    mapping_data = []
    sorted_types = sorted(task_type_counts.items(), key=lambda x: x[1], reverse=True)
    
    for task_type, count in sorted_types:
        task_ids = sorted(task_type_to_ids[task_type])
        mapping_data.append({
            'task_type': task_type,
            'count': count,
            'task_ids': ', '.join(map(str, task_ids)),
            'num_tasks': len(task_ids)
        })
    
    # Create DataFrame and save
    mapping_df = pd.DataFrame(mapping_data)
    mapping_df.to_csv(mapping_path, index=False)
    print(f"Task type to ID mapping saved to: {mapping_path}")
    
    return mapping_path

def save_statistics(task_type_counts, output_dir='.'):
    """
    Save detailed statistics to a text file.
    """
    stats_path = os.path.join(output_dir, 'task_types_statistics.txt')
    
    with open(stats_path, 'w') as f:
        f.write("Task Type Distribution Analysis\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total unique task types: {len(task_type_counts)}\n")
        f.write(f"Total task type instances: {sum(task_type_counts.values())}\n\n")
        
        f.write("Task Type Counts (sorted by frequency):\n")
        f.write("-" * 40 + "\n")
        
        sorted_types = sorted(task_type_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (task_type, count) in enumerate(sorted_types, 1):
            f.write(f"{i:3d}. {task_type:<40} : {count:3d}\n")
        
        f.write("\n" + "=" * 50 + "\n")
        f.write("Summary Statistics:\n")
        f.write(f"Most common task type: {sorted_types[0][0]} ({sorted_types[0][1]} occurrences)\n")
        f.write(f"Least common task type: {sorted_types[-1][0]} ({sorted_types[-1][1]} occurrences)\n")
        
        # Calculate some additional statistics
        counts = list(task_type_counts.values())
        f.write(f"Mean count per task type: {sum(counts)/len(counts):.2f}\n")
        f.write(f"Median count: {sorted(counts)[len(counts)//2]}\n")
        
        # Count task types that appear only once
        single_occurrence = sum(1 for count in counts if count == 1)
        f.write(f"Task types appearing only once: {single_occurrence} ({single_occurrence/len(counts)*100:.1f}%)\n")
        
        # Count task types that appear 5+ times
        frequent_types = sum(1 for count in counts if count >= 5)
        f.write(f"Task types appearing 5+ times: {frequent_types} ({frequent_types/len(counts)*100:.1f}%)\n")
    
    print(f"Statistics saved to: {stats_path}")

def compare_datasets(test_counts, dev_counts, test_mapping, dev_mapping):
    """
    Create a side-by-side comparison of task type distributions between test and dev sets.
    """
    print("\n" + "="*100)
    print("SIDE-BY-SIDE COMPARISON: TEST SET vs DEV SET")
    print("="*100)
    
    # Get all unique task types from both sets
    all_task_types = set(test_counts.keys()) | set(dev_counts.keys())
    all_task_types = sorted(all_task_types)
    
    # Create comparison table
    print(f"{'Task Type':<35} {'Test Count':<12} {'Dev Count':<12} {'Test IDs':<20} {'Dev IDs':<20}")
    print("-" * 100)
    
    for task_type in all_task_types:
        test_count = test_counts.get(task_type, 0)
        dev_count = dev_counts.get(task_type, 0)
        
        # Format task IDs for display
        test_ids = sorted(test_mapping.get(task_type, []))
        dev_ids = sorted(dev_mapping.get(task_type, []))
        
        # Show ALL task IDs without truncation
        test_ids_str = ", ".join(map(str, test_ids)) if test_ids else "-"
        dev_ids_str = ", ".join(map(str, dev_ids)) if dev_ids else "-"
        
        print(f"{task_type:<35} {test_count:<12} {dev_count:<12} {test_ids_str:<20} {dev_ids_str:<20}")
    
    print("\n" + "="*100)
    
    # Summary statistics
    print("SUMMARY STATISTICS:")
    print(f"Total unique task types in test set: {len(test_counts)}")
    print(f"Total unique task types in dev set: {len(dev_counts)}")
    print(f"Task types in both sets: {len(set(test_counts.keys()) & set(dev_counts.keys()))}")
    print(f"Task types only in test set: {len(set(test_counts.keys()) - set(dev_counts.keys()))}")
    print(f"Task types only in dev set: {len(set(dev_counts.keys()) - set(test_counts.keys()))}")
    
    # Most common differences
    print("\nTOP 10 TASK TYPES BY FREQUENCY DIFFERENCE:")
    print("-" * 60)
    differences = []
    for task_type in all_task_types:
        test_count = test_counts.get(task_type, 0)
        dev_count = dev_counts.get(task_type, 0)
        diff = test_count - dev_count
        differences.append((task_type, test_count, dev_count, diff))
    
    differences.sort(key=lambda x: abs(x[3]), reverse=True)
    
    print(f"{'Task Type':<35} {'Test':<6} {'Dev':<6} {'Diff':<6}")
    print("-" * 60)
    for task_type, test_count, dev_count, diff in differences[:10]:
        print(f"{task_type:<35} {test_count:<6} {dev_count:<6} {diff:+6}")

def save_comparison_csv(test_counts, dev_counts, test_mapping, dev_mapping, output_dir='.'):
    """
    Save the comparison data to a CSV file.
    """
    comparison_path = os.path.join(output_dir, 'test_dev_comparison.csv')
    
    # Get all unique task types
    all_task_types = set(test_counts.keys()) | set(dev_counts.keys())
    all_task_types = sorted(all_task_types)
    
    # Prepare data for CSV
    comparison_data = []
    for task_type in all_task_types:
        test_count = test_counts.get(task_type, 0)
        dev_count = dev_counts.get(task_type, 0)
        test_ids = sorted(test_mapping.get(task_type, []))
        dev_ids = sorted(dev_mapping.get(task_type, []))
        
        comparison_data.append({
            'task_type': task_type,
            'test_count': test_count,
            'dev_count': dev_count,
            'difference': test_count - dev_count,
            'test_task_ids': ', '.join(map(str, test_ids)) if test_ids else '',
            'dev_task_ids': ', '.join(map(str, dev_ids)) if dev_ids else '',
            'in_both_sets': task_type in test_counts and task_type in dev_counts
        })
    
    # Create DataFrame and save
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv(comparison_path, index=False)
    print(f"Comparison data saved to: {comparison_path}")
    
    return comparison_path

def main():
    """
    Main function to run the analysis.
    """
    # Path to the CSV files
    csv_file_path_test_set = '/Users/sanjari/orby/subtask_benchmark/scripts/csvs/online/tasks_test_09152025_3.csv'
    csv_file_path_dev_set = '/Users/sanjari/orby/subtask_benchmark/scripts/csvs/online/tasks_dev_08202025.csv'
    
    # Output directory
    output_dir = '/Users/sanjari/orby/subtask_benchmark/scripts'
    
    # Check if files exist
    if not os.path.exists(csv_file_path_test_set):
        print(f"Error: Test CSV file not found at {csv_file_path_test_set}")
        return
    
    if not os.path.exists(csv_file_path_dev_set):
        print(f"Error: Dev CSV file not found at {csv_file_path_dev_set}")
        return
    
    print("ANALYZING TEST SET...")
    print("="*50)
    # Analyze the test set
    test_result = analyze_task_types(csv_file_path_test_set)
    if test_result is None:
        return
    
    test_task_type_counts, test_df, test_task_type_to_ids = test_result
    
    print("\nANALYZING DEV SET...")
    print("="*50)
    # Analyze the dev set
    dev_result = analyze_task_types(csv_file_path_dev_set)
    if dev_result is None:
        return
    
    dev_task_type_counts, dev_df, dev_task_type_to_ids = dev_result
    
    # Print individual summaries - ALL task types, no truncation
    print("\nTEST SET SUMMARY (ALL TASK TYPES):")
    print("-" * 50)
    test_sorted_types = sorted(test_task_type_counts.items(), key=lambda x: x[1], reverse=True)
    for i, (task_type, count) in enumerate(test_sorted_types, 1):
        print(f"{i:2d}. {task_type:<35} : {count:3d}")
    
    print("\nDEV SET SUMMARY (ALL TASK TYPES):")
    print("-" * 50)
    dev_sorted_types = sorted(dev_task_type_counts.items(), key=lambda x: x[1], reverse=True)
    for i, (task_type, count) in enumerate(dev_sorted_types, 1):
        print(f"{i:2d}. {task_type:<35} : {count:3d}")
    
    # Create side-by-side comparison
    compare_datasets(test_task_type_counts, dev_task_type_counts, 
                    test_task_type_to_ids, dev_task_type_to_ids)
    
    # Create visualizations for test set
    print("\nCreating visualizations for test set...")
    fig_test = create_visualizations(test_task_type_counts, output_dir)
    plt.savefig(os.path.join(output_dir, 'test_set_distribution.png'), dpi=300, bbox_inches='tight')
    
    # Create visualizations for dev set
    print("Creating visualizations for dev set...")
    fig_dev = create_visualizations(dev_task_type_counts, output_dir)
    plt.savefig(os.path.join(output_dir, 'dev_set_distribution.png'), dpi=300, bbox_inches='tight')
    
    # Save detailed statistics for both sets
    print("Saving detailed statistics...")
    save_statistics(test_task_type_counts, output_dir)
    with open(os.path.join(output_dir, 'dev_set_statistics.txt'), 'w') as f:
        f.write("DEV SET STATISTICS\n")
        f.write("="*50 + "\n\n")
        f.write(f"Total unique task types: {len(dev_task_type_counts)}\n")
        f.write(f"Total task type instances: {sum(dev_task_type_counts.values())}\n\n")
        f.write("Task Type Counts (sorted by frequency):\n")
        f.write("-" * 40 + "\n")
        for i, (task_type, count) in enumerate(dev_sorted_types, 1):
            f.write(f"{i:3d}. {task_type:<40} : {count:3d}\n")
    
    # Save task type to ID mappings
    print("Saving task type to ID mappings...")
    save_task_type_mapping(test_task_type_to_ids, test_task_type_counts, output_dir)
    
    # Save dev set mapping with different filename
    dev_mapping_path = os.path.join(output_dir, 'dev_set_task_type_to_ids_mapping.csv')
    mapping_data = []
    for task_type, count in dev_sorted_types:
        task_ids = sorted(dev_task_type_to_ids[task_type])
        mapping_data.append({
            'task_type': task_type,
            'count': count,
            'task_ids': ', '.join(map(str, task_ids)),
            'num_tasks': len(task_ids)
        })
    dev_mapping_df = pd.DataFrame(mapping_data)
    dev_mapping_df.to_csv(dev_mapping_path, index=False)
    print(f"Dev set mapping saved to: {dev_mapping_path}")
    
    # Save comparison data
    print("Saving comparison data...")
    save_comparison_csv(test_task_type_counts, dev_task_type_counts, 
                       test_task_type_to_ids, dev_task_type_to_ids, output_dir)
    
    # Show the plots
    plt.show()
    
    print(f"\nAnalysis complete! Check the output directory: {output_dir}")
    print("Files created:")
    print(f"  - test_set_distribution.png")
    print(f"  - dev_set_distribution.png")
    print(f"  - task_types_statistics.txt")
    print(f"  - dev_set_statistics.txt")
    print(f"  - task_type_to_ids_mapping.csv (test set)")
    print(f"  - dev_set_task_type_to_ids_mapping.csv")
    print(f"  - test_dev_comparison.csv")

if __name__ == "__main__":
    main()
