import GPy as gp
import pandas as pd
import numpy as np
import os
import sys


class KroghSearch:
    _allowed_targets = {'pbO2', 'jvO2_sat'}

    def __init__(self, target_name):
        if target_name not in self._allowed_targets:
            raise ValueError("target_name must be one of %s" % self._allowed_targets)
        feature_columns = ['CMRO2', 'vel', 'D', 'r_Krogh', 'paO2', 'Hb']

        folder = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
        df = pd.read_csv(os.path.join(folder, "training_data.csv"))

        raw_features = df[feature_columns]
        self._features_min = raw_features.min().values
        features_max = raw_features.max().values
        self._features_range = features_max - self._features_min

        raw_labels = df[target_name]
        self._target_min = raw_labels.min()
        target_max = raw_labels.max()
        self._target_range = target_max - self._target_min

        features = self._normalize_features(raw_features.values)
        labels = ((raw_labels - self._target_min) / self._target_range).as_matrix()[np.newaxis].T
        self.model = gp.models.GPRegression(features, labels)
        self.model.optimize()

    def predict(self, CMRO2, vel, D, r_Krogh, paO2, Hb):
        raw_features = np.array([[CMRO2, vel, D, r_Krogh, paO2, Hb]])
        features = self._normalize_features(raw_features)
        prediction = self.model.predict(features)[0]
        return self._unnormalize_target(prediction[0, 0])

    def _normalize_features(self, features):
        return (features - self._features_min) / self._features_range

    def _unnormalize_target(self, target):
        return target * self._target_range + self._target_min
