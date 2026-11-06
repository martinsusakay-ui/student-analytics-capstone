"""
ml_oulad.py - Machine Learning untuk dataset OULAD
Model: Random Forest Classification
Target: final_result (Pass/Fail/Withdrawn/Distinction)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings("ignore")


def build_oulad_features(df_vle, df_assessment, df_students):
    """
    Bangun fitur dari OULAD dataset.
    
    Args:
        df_vle: DataFrame dari collection 'oulad_vle'
        df_assessment: DataFrame dari collection 'oulad_assessment'
        df_students: DataFrame dari collection 'oulad_students'
    """
    if df_students.empty:
        return pd.DataFrame()
    
    # Ambil target dari studentInfo
    students = df_students[["id_student", "final_result"]].drop_duplicates("id_student")
    
    # Fitur dari VLE (total klik per student)
    if not df_vle.empty:
        vle_features = df_vle.groupby("id_student").agg(
            total_clicks=("sum_click", "sum"),
            avg_clicks=("sum_click", "mean"),
            n_sites=("id_site", "nunique"),
            n_days_active=("date", "nunique"),
            first_day=("date", "min"),
            last_day=("date", "max"),
        ).reset_index()
        vle_features["activity_span"] = (
            vle_features["last_day"] - vle_features["first_day"]
        ).clip(lower=1)
    else:
        vle_features = pd.DataFrame({"id_student": students["id_student"]})
    
    # Fitur dari Assessment
    if not df_assessment.empty:
        assess_features = df_assessment.groupby("id_student").agg(
            n_assessments=("id_assessment", "nunique"),
            avg_score=("score", "mean"),
            max_score=("score", "max"),
            min_score=("score", "min"),
            std_score=("score", "std"),
        ).reset_index()
        assess_features["std_score"] = assess_features["std_score"].fillna(0)
    else:
        assess_features = pd.DataFrame({"id_student": students["id_student"]})
    
    # Merge semua
    data = students.merge(vle_features, on="id_student", how="left")
    data = data.merge(assess_features, on="id_student", how="left")
    data = data.fillna(0)
    
    return data


def run_oulad_classification(df_vle, df_assessment, df_students):
    """
    Random Forest Classification untuk prediksi final_result.
    
    Returns:
        dict dengan metrics, feature_importance, sample_predictions, confusion_matrix
    """
    data = build_oulad_features(df_vle, df_assessment, df_students)
    if data.empty or len(data) < 30:
        return {"error": "Data tidak cukup untuk classification (min 30 students)"}
    
    # Filter hanya final_result yang valid (bukan '?')
    data = data[data["final_result"].notna()]
    data = data[~data["final_result"].isin(["?", ""])]
    
    if len(data) < 30:
        return {"error": "Data final_result terlalu sedikit"}
    
    # Encode target
    le = LabelEncoder()
    data["target_encoded"] = le.fit_transform(data["final_result"])
    
    # Fitur
    feature_cols = [
        "total_clicks", "avg_clicks", "n_sites", "n_days_active",
        "activity_span", "n_assessments", "avg_score", "max_score",
        "min_score", "std_score",
    ]
    feature_cols = [c for c in feature_cols if c in data.columns]
    
    X = data[feature_cols].fillna(0).values
    y = data["target_encoded"].values
    
    # Split (stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)
    
    # Predict
    y_pred = model.predict(X_test)
    
    # Metrics
    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
    recall = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
    f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
    
    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    
    # Feature importance
    importances = model.feature_importances_
    feature_importance = sorted(
        [{"feature": f, "importance": round(float(i), 4)}
         for f, i in zip(feature_cols, importances)],
        key=lambda x: -x["importance"]
    )
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    cm_list = cm.tolist()
    class_labels = list(le.classes_)
    
    # Classification report
    report = classification_report(
        y_test, y_pred,
        target_names=class_labels,
        output_dict=True,
        zero_division=0
    )
    
    # Sample predictions
    sample_data = data.head(10)
    sample_pred = model.predict(sample_data[feature_cols].fillna(0).values)
    sample_pred_labels = le.inverse_transform(sample_pred)
    
    sample_predictions = []
    for i, (_, row) in enumerate(sample_data.iterrows()):
        sample_predictions.append({
            "id_student": int(row["id_student"]),
            "actual": row["final_result"],
            "predicted": sample_pred_labels[i],
            "correct": row["final_result"] == sample_pred_labels[i],
        })
    
    return {
        "dataset": "OULAD",
        "model": "RandomForestClassifier",
        "target": "final_result",
        "classes": class_labels,
        "n_samples": len(data),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
            "cv_accuracy_std": round(float(cv_scores.std()), 4),
        },
        "feature_importance": feature_importance,
        "confusion_matrix": cm_list,
        "classification_report": report,
        "sample_predictions": sample_predictions,
    }