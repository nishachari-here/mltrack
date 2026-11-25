import mlflow
import mlflow.sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

def train_and_log_model():
    # 1. Configure MLflow to use a local SQLite database file
    mlflow.set_tracking_uri("sqlite:///mlruns.db")
    
    # 2. Set or create an MLflow experiment
    experiment_name = "ModelTrace_Baseline_Experiments"
    mlflow.set_experiment(experiment_name)
    
    print(f"Tracking MLflow experiments to database: mlruns.db")
    
    # 3. Load sample dataset (Breast Cancer Classification)
    data = load_breast_cancer()
    X_train, X_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.2, random_state=42
    )
    
    # Define hyperparameters to test across runs
    n_estimators = 100
    max_depth = 5
    min_samples_split = 4
    
    # 4. Start MLflow Run
    with mlflow.start_run(run_name="RandomForest_Baseline_Run") as run:
        print(f"Starting active MLflow run ID: {run.info.run_id}")
        
        # Log hyperparameters
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_param("min_samples_split", min_samples_split)
        mlflow.log_param("model_type", "RandomForestClassifier")
        
        # Initialize and train model
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42
        )
        model.fit(X_train, y_train)
        
        # Predict and compute evaluation metrics
        predictions = model.predict(X_test)
        acc = accuracy_score(y_test, predictions)
        precision = precision_score(y_test, predictions)
        recall = recall_score(y_test, predictions)
        f1 = f1_score(y_test, predictions)
        
        # Log metrics to MLflow database
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)
        
        # Log the trained model artifact
        mlflow.sklearn.log_model(
            model, 
            "random_forest_model",
            skops_trusted_types=["sklearn.tree._tree.Tree"]
        )
        
        print("Model training complete and metadata logged to MLflow successfully!")
        print(f"Metrics -> Accuracy: {acc:.4f}, F1-Score: {f1:.4f}")

if __name__ == "__main__":
    train_and_log_model()