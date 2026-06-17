#!/usr/bin/env python3
"""
Visualize button input timeline for each user
Shows how buttons are pressed over time for each main user
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path

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

def create_timeline_heatmap(df, user):
    """Create heatmap showing button presses over time for a user"""
    user_data = df[df['user'] == user].copy()

    if len(user_data) == 0:
        print(f"  Warning: No data for user {user}")
        return None

    # Select button columns
    available_cols = [col for col in BUTTON_COLS if col in user_data.columns]
    button_data = user_data[available_cols].iloc[:500]  # Sample first 500 frames

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    # Create heatmap
    sns.heatmap(button_data.T, cmap='YlOrRd', cbar_kws={'label': 'Button Press'},
                ax=ax, xticklabels=50, yticklabels=True)

    ax.set_title(f'Button Input Timeline - {user.upper()} (First 500 frames)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Frame Number', fontsize=12)
    ax.set_ylabel('Button', fontsize=12)

    plt.tight_layout()
    return fig

def create_button_frequency(df, user):
    """Create bar chart showing button press frequency"""
    user_data = df[df['user'] == user].copy()

    if len(user_data) == 0:
        return None

    available_cols = [col for col in BUTTON_COLS if col in user_data.columns]

    # Calculate frequency
    frequencies = user_data[available_cols].sum().sort_values(ascending=False)
    frequencies = frequencies[frequencies > 0]  # Only show used buttons

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = plt.cm.Set3(np.linspace(0, 1, len(frequencies)))
    ax.bar(range(len(frequencies)), frequencies.values, color=colors)
    ax.set_xticks(range(len(frequencies)))
    ax.set_xticklabels(frequencies.index, rotation=45, ha='right')

    ax.set_title(f'Button Press Frequency - {user.upper()}', fontsize=14, fontweight='bold')
    ax.set_ylabel('Total Presses', fontsize=12)
    ax.set_xlabel('Button', fontsize=12)

    plt.tight_layout()
    return fig

def create_combo_frequency(df, user):
    """Create visualization of button combinations"""
    user_data = df[df['user'] == user].copy()

    if len(user_data) == 0:
        return None

    combo_cols = ['Right_Jump', 'Left_Jump', 'Right_Kick', 'Left_Kick',
                  'Punch_Kick', 'Jump_Punch', 'Shoryuken', 'Hadoken']
    available_combos = [col for col in combo_cols if col in user_data.columns]

    combos = user_data[available_combos].sum()
    combos = combos[combos > 0]

    if len(combos) == 0:
        return None

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = plt.cm.Spectral(np.linspace(0, 1, len(combos)))
    ax.bar(range(len(combos)), combos.values, color=colors)
    ax.set_xticks(range(len(combos)))
    ax.set_xticklabels(combos.index, rotation=45, ha='right')

    ax.set_title(f'Button Combination Frequency - {user.upper()}', fontsize=14, fontweight='bold')
    ax.set_ylabel('Total Times Used', fontsize=12)
    ax.set_xlabel('Combination', fontsize=12)

    plt.tight_layout()
    return fig

def create_comparison_heatmap(df):
    """Create comparison heatmap for all users"""
    fig, axes = plt.subplots(len(MAIN_USERS), 1, figsize=(14, 3*len(MAIN_USERS)))

    if len(MAIN_USERS) == 1:
        axes = [axes]

    available_cols = [col for col in BUTTON_COLS if col in df.columns]

    for idx, user in enumerate(MAIN_USERS):
        user_data = df[df['user'] == user].copy()

        if len(user_data) == 0:
            axes[idx].text(0.5, 0.5, f'No data for {user}',
                          ha='center', va='center', fontsize=12)
            axes[idx].axis('off')
            continue

        button_data = user_data[available_cols].iloc[:300]

        sns.heatmap(button_data.T, cmap='YlOrRd', cbar=False,
                   ax=axes[idx], xticklabels=50, yticklabels=True)
        axes[idx].set_title(f'{user.upper()}', fontsize=12, fontweight='bold')
        axes[idx].set_ylabel('Button', fontsize=10)

        if idx == len(MAIN_USERS) - 1:
            axes[idx].set_xlabel('Frame Number', fontsize=10)

    plt.tight_layout()
    return fig

def main():
    print("Loading feature data...")
    df = load_data()

    print(f"Loaded {len(df)} records")
    print(f"Users in data: {sorted(df['user'].unique())}\n")

    output_dir = 'create_model2/output/visualizations'
    os.makedirs(output_dir, exist_ok=True)

    # Create individual visualizations for each user
    print("Creating individual user visualizations...")
    for user in MAIN_USERS:
        user_count = (df['user'] == user).sum()
        if user_count == 0:
            print(f"  Skipping {user} (no data)")
            continue

        print(f"  Processing {user} ({user_count:,} records)")

        # Timeline heatmap
        fig = create_timeline_heatmap(df, user)
        if fig:
            fig.savefig(f'{output_dir}/{user}_timeline_heatmap.png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            print(f"    ✓ Saved timeline heatmap")

        # Frequency chart
        fig = create_button_frequency(df, user)
        if fig:
            fig.savefig(f'{output_dir}/{user}_button_frequency.png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            print(f"    ✓ Saved frequency chart")

        # Combo frequency
        fig = create_combo_frequency(df, user)
        if fig:
            fig.savefig(f'{output_dir}/{user}_combo_frequency.png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            print(f"    ✓ Saved combo frequency chart")

    # Create comparison visualization
    print("\nCreating comparison visualization...")
    fig = create_comparison_heatmap(df)
    fig.savefig(f'{output_dir}/all_users_comparison.png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    print("✓ Saved comparison heatmap")

    print(f"\n✅ All visualizations saved to: {output_dir}")
    print(f"Generated files:")
    for file in sorted(os.listdir(output_dir)):
        file_path = os.path.join(output_dir, file)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path) / 1024
            print(f"  - {file} ({size:.1f} KB)")

if __name__ == '__main__':
    main()
