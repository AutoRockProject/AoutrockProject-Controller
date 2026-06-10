#!/usr/bin/env python3
"""
Feature Engineering Script for Fighting Game Decision Tree Model
Extracts and creates features from CSV controller input data
"""

import pandas as pd
import numpy as np
import glob
import os
from pathlib import Path

def detect_command(row_current, row_prev, row_prev2, row_prev3):
    """
    Detect special commands based on controller inputs
    - Shoryuken (昇竜拳): → ↓ ↘ + Punch (A)
    - Hadoken (波動拳): ↓ ↘ → + Punch (A)
    """
    shoryuken = 0
    hadoken = 0

    # Check if punch button (A) is pressed in current frame
    if row_current['A'] == 1:
        # Shoryuken: Right -> Down -> DownRight + A
        if (row_prev3['RightArrow'] == 1 and
            row_prev2['DownArrow'] == 1 and
            row_prev['DownRightArrow'] == 1):
            shoryuken = 1

        # Hadoken: Down -> DownRight -> Right + A
        if (row_prev3['DownArrow'] == 1 and
            row_prev2['DownRightArrow'] == 1 and
            row_prev['RightArrow'] == 1):
            hadoken = 1

    return shoryuken, hadoken

def extract_features(csv_file):
    """
    Extract features from a single CSV file
    """
    # Read CSV
    df = pd.read_csv(csv_file)
    df = df.fillna(0)  # Fill NaN values with 0
    df = df.copy()

    # Extract user names from filename
    # Format: 20260513_user1_user2_match_number.csv
    filename = Path(csv_file).stem
    parts = filename.split('_')
    user1 = parts[1]
    user2 = parts[2]
    match_number = int(parts[3])  # 1 or 2

    # Get all unique users in the CSV
    users = df['username'].unique()

    # Create features for each row
    features = []

    for idx in range(len(df)):
        row = df.iloc[idx]
        user = row['username']

        # Determine if this is player 1 or player 2 based on StateX
        # Positive StateX = right side, Negative StateX = left side
        state_x = float(row['StateX'])

        # Standing position (right/left based on StateX sign)
        standing_right = 1 if state_x > 0 else 0
        standing_left = 1 if state_x <= 0 else 0

        # Body direction (assume from historical input pattern)
        # For simplicity, using RightArrow/LeftArrow as proxy for facing direction
        facing_right = float(row['Right'])  # normalized input
        facing_left = float(row['Left'])
        body_right = 1 if facing_right > facing_left else 0
        body_left = 1 if facing_left > facing_right else 0

        # Button combinations
        right_jump = 1 if (float(row['Right']) == 1 and float(row['Up']) == 1) else 0
        left_jump = 1 if (float(row['Left']) == 1 and float(row['Up']) == 1) else 0
        right_kick = 1 if (float(row['Right']) == 1 and float(row['B']) == 1) else 0
        left_kick = 1 if (float(row['Left']) == 1 and float(row['B']) == 1) else 0
        punch_kick = 1 if (float(row['A']) == 1 and float(row['B']) == 1) else 0
        jump_punch = 1 if (float(row['Up']) == 1 and float(row['A']) == 1) else 0

        # Special commands
        shoryuken = 0
        hadoken = 0

        # Need previous frames for command detection
        if idx >= 3:
            row_prev = df.iloc[idx - 1]
            row_prev2 = df.iloc[idx - 2]
            row_prev3 = df.iloc[idx - 3]

            # Only detect if same user
            if (row['username'] == row_prev['username'] and
                row_prev['username'] == row_prev2['username'] and
                row_prev2['username'] == row_prev3['username']):
                shoryuken, hadoken = detect_command(row, row_prev, row_prev2, row_prev3)

        # Button state dummies
        feature_row = {
            'timestamp': row['Timestamp'],
            'user': user,
            'match_number': match_number,
            'user1': user1,
            'user2': user2,

            # Video-extracted features
            'standing_right': standing_right,
            'standing_left': standing_left,
            'body_right': body_right,
            'body_left': body_left,

            # Button inputs
            'A': int(row['A']),
            'B': int(row['B']),
            'RB': int(row['RB']),
            'LB': int(row['LB']),
            'RT': int(row['RT']),
            'LT': int(row['LT']),
            'SELECT': int(row['SELECT']),
            'START': int(row['START']),

            # Direction inputs
            'Up': int(row['Up']),
            'Down': int(row['Down']),
            'Left': int(row['Left']),
            'Right': int(row['Right']),
            'UpLeft': int(row['UpLeft']),
            'UpRight': int(row['UpRight']),
            'DownLeft': int(row['DownLeft']),
            'DownRight': int(row['DownRight']),

            # Special moves
            'Shoryuken': shoryuken,
            'Hadoken': hadoken,

            # Button combinations
            'Right_Jump': right_jump,
            'Left_Jump': left_jump,
            'Right_Kick': right_kick,
            'Left_Kick': left_kick,
            'Punch_Kick': punch_kick,
            'Jump_Punch': jump_punch,
        }

        features.append(feature_row)

    features_df = pd.DataFrame(features)
    return features_df, user1, user2, match_number

def main():
    """
    Main function to process all CSV files and create features
    """
    csv_files = sorted(glob.glob('20260513/*.csv'))

    all_data = []

    print("Processing CSV files...")
    for csv_file in csv_files:
        print(f"  Processing: {os.path.basename(csv_file)}")
        try:
            features_df, user1, user2, match_num = extract_features(csv_file)
            all_data.append(features_df)
        except Exception as e:
            print(f"    Error processing {csv_file}: {e}")
            continue

    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)

    # Save combined features
    output_path = 'create_model/output/all_features.csv'
    combined_df.to_csv(output_path, index=False)
    print(f"\nSaved combined features to {output_path}")
    print(f"Total records: {len(combined_df)}")
    print(f"Feature columns: {list(combined_df.columns)}")

    return combined_df

if __name__ == '__main__':
    features_df = main()
    print("\nFeature engineering completed!")
