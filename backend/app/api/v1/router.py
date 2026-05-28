from fastapi import APIRouter

from app.api.v1 import (
    account,
    admin,
    ai_runs,
    api_keys,
    auth,
    billing,
    content,
    expiry,
    exports,
    families,
    opportunity,
    patents,
    reports,
    search,
    semantic_search,
    subscriptions,
    suppliers,
    themes,
    trends,
    usage_signals,
    watchlist,
)

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(patents.router, prefix="/patents", tags=["patents"])
v1_router.include_router(search.router, prefix="/search", tags=["search"])
v1_router.include_router(semantic_search.router, prefix="/semantic", tags=["semantic-search"])
v1_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
v1_router.include_router(expiry.router, prefix="/expiry", tags=["expiry"])
v1_router.include_router(families.router, prefix="/families", tags=["families"])
v1_router.include_router(themes.router, prefix="/themes", tags=["themes"])
v1_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
v1_router.include_router(ai_runs.router, prefix="/ai-runs", tags=["ai-runs"])
v1_router.include_router(opportunity.router, prefix="/opportunity", tags=["opportunity"])
v1_router.include_router(trends.router, prefix="/trends", tags=["trends"])
v1_router.include_router(content.router, prefix="/content", tags=["content"])
v1_router.include_router(usage_signals.router, prefix="/usage-signals", tags=["usage-signals"])
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
v1_router.include_router(billing.router, prefix="/billing", tags=["billing"])
v1_router.include_router(exports.router, prefix="/exports", tags=["exports"])
v1_router.include_router(reports.router, prefix="/patents", tags=["reports"])
v1_router.include_router(api_keys.router, prefix="/account", tags=["api-keys"])
v1_router.include_router(account.router, prefix="/account", tags=["account"])
