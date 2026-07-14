from fastapi import APIRouter

from app.api.dependencies import CurrentUser, Database
from app.schemas.stats import StatsOverview
from app.services.stats import StatsService

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/overview", response_model=StatsOverview)
def overview(user: CurrentUser, db: Database) -> StatsOverview:
    return StatsService(db).overview(user)
