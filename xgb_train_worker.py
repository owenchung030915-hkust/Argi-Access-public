#!/usr/bin/env python3
"""Isolated XGBoost trainer subprocess (avoids torch/XGBoost native conflicts on macOS)."""

import pickle
import sys

import numpy as np
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor


def build_xgboost_model():
    return MultiOutputRegressor(
        XGBRegressor(
            n_estimators=80,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=1,
            tree_method='hist',
            objective='reg:squarederror',
        )
    )


if __name__ == '__main__':
    input_path, output_path = sys.argv[1], sys.argv[2]
    data = np.load(input_path)
    model = build_xgboost_model()
    model.fit(data['X'], data['y'])
    with open(output_path, 'wb') as output_file:
        pickle.dump(model, output_file)
