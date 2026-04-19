from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes.helpers import serialize_article_list_item
from app.db.session import get_db
from app.schemas.dashboard import DashboardOut
from app.services.dashboard import DashboardService

router = APIRouter()
service = DashboardService()


@router.get("", response_model=DashboardOut, summary="Dashboard metrics")
def get_dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    data = service.get_dashboard(db)
    data["latest_articles"] = [
        serialize_article_list_item(item) for item in data["latest_articles"]
    ]
    return DashboardOut(**data)
