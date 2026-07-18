from fastapi import APIRouter

from app.api.routes import auth, machines, programs, stats, workout_templates, workouts

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(machines.router)
api_router.include_router(workouts.router)
api_router.include_router(workout_templates.router)
api_router.include_router(programs.router)
api_router.include_router(stats.router)
