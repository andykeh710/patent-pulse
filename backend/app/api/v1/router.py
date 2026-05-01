from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai_runs,
    expiry,
    families,
    opportunity,
    patents,
    search,
    semantic_search,
    themes,
    watchlist,
)

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(patents.router, prefix="/patents", tags=["patents"])
v1_router.include_router(search.router, prefix="/search", tags=["search"])
v1_router.include_router(semantic_search.router, prefix="/semantic", tags=["semantic-search"])
v1_router.include_router(expiry.router, prefix="/expiry", tags=["expiry"])
v1_router.include_router(families.router, prefix="/families", tags=["families"])
v1_router.include_router(themes.router, prefix="/themes", tags=["themes"])
v1_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
v1_router.include_router(ai_runs.router, prefix="/ai-runs", tags=["ai-runs"])
v1_router.include_router(opportunity.router, prefix="/opportunity", tags=["opportunity"])
