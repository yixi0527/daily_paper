from fastapi import APIRouter

from app.api.routes import articles, dashboard, health, journals, search, sync

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(journals.router, prefix="/journals", tags=["journals"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
