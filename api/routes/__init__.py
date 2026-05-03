"""Centralised router registration.

Import all routers here so ``main.py`` can register them in a single loop.
"""

from .api_admin import router as api_admin_router
from .api_company_blacklist import router as api_company_blacklist_router
from .api_cv import router as api_cv_router
from .api_dashboard import router as api_dashboard_router
from .api_lists import router as api_lists_router
from .api_pipeline import router as api_pipeline_router
from .api_platforms import router as api_platforms_router
from .api_profile import router as api_profile_router
from .api_results import router as api_results_router
from .api_search_config import router as api_search_config_router
from .api_version import router as api_version_router
from .auth import router as auth_router

all_routers = [
    auth_router,
    api_dashboard_router,
    api_results_router,
    api_profile_router,
    api_search_config_router,
    api_pipeline_router,
    api_lists_router,
    api_admin_router,
    api_company_blacklist_router,
    api_cv_router,
    api_platforms_router,
    api_version_router,
]
