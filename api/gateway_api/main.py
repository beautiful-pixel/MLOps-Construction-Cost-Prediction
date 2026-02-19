from fastapi import FastAPI

from routers.training import router as training_router
from routers.pipeline import router as pipeline_router
from routers.models import router as models_router
from routers.experiments import router as experiments_router
from routers.inference import router as inference_router
from routers.system import router as system_router
from routers.configs import router as configs_router
from routers.auth import router as auth_router
from routers import features
from routers import data_contract
from routers import model_schemas


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
app.include_router(inference_router)
app.include_router(configs_router)
app.include_router(auth_router)
app.include_router(features.router)
app.include_router(data_contract.router)
app.include_router(model_schemas.router)
