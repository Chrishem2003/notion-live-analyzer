# Performance Optimization TODO

## 1. Fix: Non-blocking dependency check ✅
- [x] Move heavy dependency imports from startup
- [x] Add lazy loading for optional heavy packages
- [x] Show non-blocking warning instead of blocking startup

## 2. Fix: Cache Notion API calls aggressively ✅
- [x] Add `st.cache_data` for database options (10 min TTL)
- [x] Add in-memory request-level caching in `notion_client.py`
- [x] Add rate limiter for Notion API requests
- [x] Add request deduplication for API calls

## 3. Fix: Reduce requirements to core only ✅
- [x] Create `requirements-optional.txt` for heavy packages
- [x] Keep only essential packages in `requirements.txt`
- [x] Update `dependency_manager.py` to handle optional installs (handled by lazy check)
- [x] Update Dockerfile with layered installs

## 4. Fix: Debounce excessive `st.rerun()` calls ✅
- [x] Add rerun debounce guard in session state
- [x] Prevent cascading reruns on refresh

## 5. Fix: Increase cache TTL from 60s to 300s ✅
- [x] Change default TTL to 300s (5 min) in config.py
- [x] Add NOTION_API_CACHE_TTL (10 min) and NOTION_DATA_CACHE_TTL (5 min)
- [x] Update Streamlit server config for performance

## 6. Fix: Docker & Render optimizations ✅
- [x] Add HEALTHCHECK to Dockerfile
- [x] Add performance env vars to render.yaml
- [x] Switch to Docker-based deployment on Render

## 7. Fix: Startup time display ✅
- [x] Show startup time in UI
- [x] Non-blocking warning for missing optional packages
- [x] Reduce pagination limits for faster first load

