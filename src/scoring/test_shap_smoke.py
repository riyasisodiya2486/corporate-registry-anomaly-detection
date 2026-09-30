"""
RUN THIS FIRST, before run_shap.py, on your own laptop.
Confirms shap + IsolationForest actually work together in your environment,
on 20 fake rows, before you trust it on your real 7,384 clusters.
"""
import numpy as np
import shap
from sklearn.ensemble import IsolationForest

np.random.seed(0)
X = np.random.rand(20, 4)
model = IsolationForest(n_estimators=50, random_state=42).fit(X)

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

print("shap_values shape:", np.array(shap_values).shape, "-- expect (20, 4)")
assert np.array(shap_values).shape == (20, 4)
print("SUCCESS: shap + IsolationForest work together in this environment")