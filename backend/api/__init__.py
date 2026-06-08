"""FastAPI surface for Boussole (Phase 7).

Import light: routes/app pull from this package but do not need anything
from regulations/* at import time, so the agent core + regulation plugins
stay decoupled from the HTTP layer.
"""
