#!/usr/bin/env python3
"""
Decision Tree Model Training Script (v2)
Filtered version: Main users only
Creates a decision tree model to predict users based on controller inputs
"""

import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import json
import os
from datetime import datetime

# Define main users to include
MAIN_USERS = ['jin', 'keita', 'kotaro', 'akira', 'ryo', 'nakamura', 'yamaguti']

def prepare_data():
    """
    Load features and prepare training/test data
    Split by: same user pair, match 1 = train, match 2 = test
    Filter to main users only
    """
    # Load features
    features_path = 'create_model2/output/all_features.csv'
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Features file not found: {features_path}")

    df = pd.read_csv(features_path)
    print(f"Loaded {len(df)} feature records (main users only)")

    # Feature columns (explanatory variables)
    # Buttons + Directions + Special features
    feature_cols = [
        'A', 'B', 'RB', 'LB', 'RT', 'LT', 'SELECT', 'START',
        'Up', 'Down', 'Left', 'Right',
        'UpLeft', 'UpRight', 'DownLeft', 'DownRight',
        'standing_right', 'standing_left', 'body_right', 'body_left',
        'Right_Jump', 'Left_Jump', 'Right_Kick', 'Left_Kick',
        'Punch_Kick', 'Jump_Punch', 'Shoryuken', 'Hadoken'
    ]

    # Check for missing columns
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        print(f"Warning: Missing columns: {missing_cols}")
        feature_cols = [col for col in feature_cols if col in df.columns]

    # Target variable: user
    target_col = 'user'

    # Create training and test sets
    # Match 1 = training, Match 2 = test
    train_df = df[df['match_number'] == 1].copy()
    test_df = df[df['match_number'] == 2].copy()

    print(f"\nData split:")
    print(f"  Train set: {len(train_df)} records")
    print(f"  Test set: {len(test_df)} records")

    X_train = train_df[feature_cols].fillna(0)
    y_train = train_df[target_col]

    X_test = test_df[feature_cols].fillna(0)
    y_test = test_df[target_col]

    print(f"\nTarget variable '{target_col}' classes:")
    print(f"  Train: {sorted(y_train.unique())}")
    print(f"  Test: {sorted(y_test.unique())}")

    print(f"\nPer-user distribution (test set):")
    for user in sorted(MAIN_USERS):
        count = (y_test == user).sum()
        if count > 0:
            print(f"  {user}: {count:,}")

    return X_train, y_train, X_test, y_test, feature_cols, train_df, test_df

def train_model(X_train, y_train):
    """
    Train decision tree model
    """
    print("\n" + "="*60)
    print("Training Decision Tree Model...")
    print("="*60)

    # Create and train model
    model = DecisionTreeClassifier(
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Training accuracy
    train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, train_pred)
    print(f"Training Accuracy: {train_acc:.4f} ({train_acc*100:.2f}%)")

    return model

def evaluate_model(model, X_test, y_test, X_train, y_train, feature_cols):
    """
    Evaluate model and compute metrics
    """
    print("\nEvaluating Model on Test Set...")

    # Test predictions
    y_pred = model.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred)

    print(f"Test Accuracy (Main Users): {test_acc:.4f} ({test_acc*100:.2f}%)")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nTop 15 Important Features:")
    print(feature_importance.head(15).to_string(index=False))

    return y_pred, test_acc, feature_importance

def compute_per_user_metrics(y_test, y_pred, test_df):
    """
    Compute per-user accuracy and feature importance
    """
    print("\n" + "="*60)
    print("Per-User Performance Metrics")
    print("="*60)

    per_user_accuracy = {}
    unique_users = sorted(test_df['user'].unique())

    for user in unique_users:
        mask = test_df['user'].values == user
        if mask.sum() > 0:
            y_test_user = y_test[mask]
            y_pred_user = y_pred[mask]
            acc = accuracy_score(y_test_user, y_pred_user)
            per_user_accuracy[user] = {
                'accuracy': float(acc),
                'test_samples': int(mask.sum())
            }
            accuracy_pct = acc * 100
            bar_length = int(accuracy_pct / 5)
            bar = '█' * bar_length + '░' * (20 - bar_length)
            print(f"  {user:12} {bar} {accuracy_pct:6.2f}% ({mask.sum():,} samples)")

    return per_user_accuracy

def save_results(model, feature_importance, per_user_accuracy, test_acc, X_train, y_train):
    """
    Save model results to output directory
    """
    output_dir = 'create_model2/output'
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. Save feature importance (model-wide)
    feature_importance_path = os.path.join(output_dir, 'model_feature_importance.csv')
    feature_importance.to_csv(feature_importance_path, index=False)
    print(f"\nSaved model feature importance to {feature_importance_path}")

    # 2. Save per-user accuracy
    per_user_acc_path = os.path.join(output_dir, 'per_user_accuracy.json')
    with open(per_user_acc_path, 'w') as f:
        json.dump(per_user_accuracy, f, indent=2)
    print(f"Saved per-user accuracy to {per_user_acc_path}")

    # 3. Save model metrics summary
    summary = {
        'timestamp': timestamp,
        'overall_test_accuracy': float(test_acc),
        'train_samples': len(X_train),
        'test_samples': len(y_train),
        'feature_columns': list(feature_importance['feature'].head(15).values),
        'per_user_accuracy': per_user_accuracy
    }

    summary_path = os.path.join(output_dir, 'model_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved model summary to {summary_path}")

    # 4. Save detailed feature importance report
    detailed_report = {
        'model_feature_importance': feature_importance.to_dict('records'),
        'per_user_accuracy': per_user_accuracy,
        'overall_accuracy': float(test_acc),
        'timestamp': timestamp
    }

    report_path = os.path.join(output_dir, 'model_report.json')
    with open(report_path, 'w') as f:
        json.dump(detailed_report, f, indent=2)
    print(f"Saved detailed report to {report_path}")

    return summary_path, feature_importance_path, per_user_acc_path

def main():
    """
    Main execution function
    """
    print("\n" + "="*60)
    print("Decision Tree Model Training Pipeline (v2)")
    print("Main Users Only - Cleaned Dataset")
    print("="*60)

    # Step 1: Prepare data
    X_train, y_train, X_test, y_test, feature_cols, train_df, test_df = prepare_data()

    # Step 2: Train model
    model = train_model(X_train, y_train)

    # Step 3: Evaluate model
    y_pred, test_acc, feature_importance = evaluate_model(
        model, X_test, y_test, X_train, y_train, feature_cols
    )

    # Step 4: Compute per-user metrics
    per_user_accuracy = compute_per_user_metrics(y_test, y_pred, test_df)

    # Step 5: Save results
    summary_path, fi_path, acc_path = save_results(
        model, feature_importance, per_user_accuracy, test_acc, X_train, y_train
    )

    print("\n" + "="*60)
    print("Model Training Complete!")
    print("="*60)
    print(f"\nResults saved to: create_model2/output/")
    print(f"Overall Test Accuracy: {test_acc*100:.2f}%")

if __name__ == '__main__':
    main()
