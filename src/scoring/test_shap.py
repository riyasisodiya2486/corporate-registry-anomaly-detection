import numpy as np
from sklearn.ensemble import IsolationForest
import shap

# Generate dummy data to test ML integration
X = np.random.rand(100, 4)
model = IsolationForest(random_state=42).fit(X)

# Verify TreeExplainer works with Isolation Forest
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

print("SHAP values shape:", shap_values.shape)
print("SUCCESS: Isolation Forest + SHAP working together")