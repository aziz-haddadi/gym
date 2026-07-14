from fastapi import APIRouter

from app.api.routes import agenda, auth, machines, stats, workouts

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(agenda.router)
api_router.include_router(machines.router)
api_router.include_router(workouts.router)
api_router.include_router(stats.router)
