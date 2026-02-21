from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest

from routers.training import router as training_router
from routers.pipeline import router as pipeline_router
from routers.models import router as models_router
from routers.experiments import router as experiments_router
from routers.inference import router as inference_router
from routers.system import router as system_router
from routers.configs import router as configs_router
from routers.auth import router as auth_router
from routers.features import router as feature_router
from routers.data_contract import router as data_contract_router
from routers.model_schemas import router as model_schemas_router
from routers.auth import router as auth_router


app = FastAPI(
    title="MLOps Gateway API",
    version="1.0",
    root_path="/api"
)

# Register routers
app.include_router(system_router)
app.include_router(models_router)
app.include_router(experiments_router)
app.include_router(training_router)
app.include_router(pipeline_router)
app.include_router(inference_router)     # user
app.include_router(configs_router)
app.include_router(auth_router)          # public
app.include_router(feature_router)
app.include_router(data_contract_router)
app.include_router(model_schemas_router)
app.include_router(auth_router)


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain",
    )
