import mlflow

def load_model_and_metadata(model_version: str):

    model_uri = f"models:/construction_model/{model_version}"
    model = mlflow.pyfunc.load_model(model_uri)

    client = mlflow.tracking.MlflowClient()
    mv = client.get_model_version("construction_model", model_version)

    feature_version = mv.tags["feature_version"]
    feature_schema = mv.tags["feature_schema"]  # stored as JSON

    return model, json.loads(feature_schema), feature_version
