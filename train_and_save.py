import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

print("Loading data...")
try:
    data = np.load("processed_data.npz")
    X_train, y_train = data['X_train'], data['y_train']
    X_test, y_test = data['X_test'], data['y_test']

    print("Training Random Forest...")
    clf = RandomForestClassifier(n_estimators=100, class_weight='balanced', n_jobs=-1, random_state=42)
    clf.fit(X_train, y_train)

    print("Evaluating...")
    preds = clf.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, preds):.4f}")
    print(classification_report(y_test, preds))

    print("Saving 'fall_model.pkl'...")
    joblib.dump(clf, "fall_model.pkl")
    print("✅ Model Saved successfully!")
except FileNotFoundError:
    print("❌ Error: processed_data.npz not found. Run data_processor.py first.")