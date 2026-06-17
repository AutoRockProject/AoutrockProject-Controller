#!/usr/bin/env python3
"""
Visualize button input timeline across multiple matches
Shows button press patterns in a timeline format for multiple matches
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import glob
from pathlib import Path

MAIN_USERS = ['jin', 'keita', 'kotaro', 'akira', 'ryo', 'nakamura', 'yamaguti']

# Button columns to visualize
BUTTON_COLS = ['A', 'B', 'RB', 'LB', 'RT', 'LT', 'SELECT', 'START',
               'Up', 'Down', 'Left', 'Right',
               'UpLeft', 'UpRight', 'DownLeft', 'DownRight',
               'Shoryuken', 'Hadoken']

def load_raw_data():
    """Load raw CSV files from 20260513 directory"""
    csv_files = sorted(glob.glob('20260513/*.csv'))[:6]  # Load first 6 matches

    all_data = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        df['match_file'] = Path(csv_file).stem
        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)

def create_timeline_visualization(df):
    """Create timeline visualization showing button presses across matches"""

    # Get unique matches
    matches = df['match_file'].unique()[:5]  # Show 5 matches
    available_cols = [col for col in BUTTON_COLS if col in df.columns]

    n_matches = len(matches)
    fig, axes = plt.subplots(n_matches, 1, figsize=(18, 3*n_matches), sharex=False)

    if n_matches == 1:
        axes = [axes]

    for idx, match in enumerate(matches):
        match_data = df[df['match_file'] == match].copy()

        # Sample data if too long
        if len(match_data) > 1000:
            match_data = match_data.iloc[::len(match_data)//1000]

        ax = axes[idx]

        # Create heatmap for this match
        button_data = match_data[available_cols].reset_index(drop=True)

        sns.heatmap(button_data.T, cmap='YlOrRd', cbar=False, ax=ax,
                   xticklabels=max(1, len(button_data)//10), yticklabels=True,
                   linewidths=0.2, linecolor='gray')

        # Get players info
        users = match_data['username'].unique()
        user_str = ' vs '.join([str(u) for u in users[:2]])

        ax.set_title(f'Match: {match} ({user_str})', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylabel('Button', fontsize=10)

        if idx == n_matches - 1:
            ax.set_xlabel('Frame Number', fontsize=10)
        else:
            ax.set_xlabel('')

    plt.suptitle('Button Input Timeline - Multiple Matches',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()

    return fig

def main():
    print("Loading raw match data...")
    df = load_raw_data()

    print(f"✓ Loaded {len(df):,} records")
    print(f"✓ Matches found: {df['match_file'].nunique()}")
    players = [str(u) for u in df['username'].dropna().unique()]
    print(f"✓ Players: {', '.join(sorted(players))}\n")

    print("Creating timeline visualization...")
    fig = create_timeline_visualization(df)

    print("✅ Visualization created successfully!")

    return fig

if __name__ == '__main__':
    fig = main()
