from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from frotad.api.routes.auth import router as auth_router
from frotad.api.routes.dashboard import router as dashboard_router
from frotad.api.routes.fleet import router as fleet_router
from frotad.api.routes.forms import router as forms_router
from frotad.api.routes.health import router as health_router
from frotad.api.routes.runner import router as runner_router
from frotad.core.config import settings
from frotad.core.http import install_http

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")


install_http(app)
app.include_router(fleet_router, prefix="/api/v1")

app.include_router(forms_router, prefix="/api/v1")

app.include_router(runner_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
