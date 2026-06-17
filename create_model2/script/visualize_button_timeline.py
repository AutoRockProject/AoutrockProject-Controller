#!/usr/bin/env python3
"""
Visualize button input timeline for each user
Shows button press patterns across all users in a single comprehensive visualization
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from io import BytesIO
import base64

# Define main users
MAIN_USERS = ['jin', 'keita', 'kotaro', 'akira', 'ryo', 'nakamura', 'yamaguti']

# Button columns to visualize
BUTTON_COLS = ['A', 'B', 'RB', 'LB', 'RT', 'LT', 'SELECT', 'START',
               'Up', 'Down', 'Left', 'Right',
               'UpLeft', 'UpRight', 'DownLeft', 'DownRight',
               'Shoryuken', 'Hadoken']

def load_data():
    """Load feature data"""
    features_path = 'create_model2/output/all_features.csv'
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Features file not found: {features_path}")

    df = pd.read_csv(features_path)
    return df

def create_comprehensive_visualization(df):
    """Create a single comprehensive visualization showing all users' button patterns"""

    # Prepare data for heatmap: users x buttons (frequency)
    available_cols = [col for col in BUTTON_COLS if col in df.columns]

    user_button_data = []
    for user in MAIN_USERS:
        user_data = df[df['user'] == user]
        if len(user_data) > 0:
            frequencies = user_data[available_cols].sum()
            user_button_data.append(frequencies)
        else:
            user_button_data.append(pd.Series(0, index=available_cols))

    # Create DataFrame for heatmap
    heatmap_df = pd.DataFrame(user_button_data, index=MAIN_USERS)

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    # 1. Heatmap of button frequencies
    ax1 = fig.add_subplot(gs[0, :])
    sns.heatmap(heatmap_df, annot=True, fmt='.0f', cmap='YlOrRd',
                cbar_kws={'label': 'Total Presses'}, ax=ax1, linewidths=0.5)
    ax1.set_title('Button Press Frequency by User', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('User', fontsize=11)
    ax1.set_xlabel('Button', fontsize=11)

    # 2. Total button presses per user
    ax2 = fig.add_subplot(gs[1, 0])
    total_presses = heatmap_df.sum(axis=1).sort_values(ascending=False)
    colors = plt.cm.viridis(np.linspace(0, 1, len(total_presses)))
    ax2.barh(range(len(total_presses)), total_presses.values, color=colors)
    ax2.set_yticks(range(len(total_presses)))
    ax2.set_yticklabels(total_presses.index)
    ax2.set_xlabel('Total Button Presses', fontsize=11)
    ax2.set_title('Total Activity per User', fontsize=12, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)

    # 3. Top buttons overall
    ax3 = fig.add_subplot(gs[1, 1])
    top_buttons = heatmap_df.sum(axis=0).sort_values(ascending=False).head(10)
    colors = plt.cm.plasma(np.linspace(0, 1, len(top_buttons)))
    ax3.bar(range(len(top_buttons)), top_buttons.values, color=colors)
    ax3.set_xticks(range(len(top_buttons)))
    ax3.set_xticklabels(top_buttons.index, rotation=45, ha='right')
    ax3.set_ylabel('Total Presses', fontsize=11)
    ax3.set_title('Top 10 Most Used Buttons', fontsize=12, fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)

    plt.suptitle('Fighting Game Button Input Analysis - All Users',
                 fontsize=16, fontweight='bold', y=0.995)

    return fig

def main():
    print("Loading feature data...")
    df = load_data()

    print(f"✓ Loaded {len(df):,} records")
    print(f"✓ Users in data: {sorted(df['user'].unique())}\n")

    print("Creating comprehensive visualization...")
    fig = create_comprehensive_visualization(df)

    # Convert to image in memory
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    plt.close(fig)

    print("✅ Visualization created successfully!")
    print(f"   Image size: {buffer.getbuffer().nbytes / 1024:.1f} KB")

    return buffer

if __name__ == '__main__':
    buffer = main()
