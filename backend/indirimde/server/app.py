"""The FastAPI app: search, device registration, watches, and a poll loop.

Thin HTTP over the pure core. `create_app` takes its collaborators (store,
repo, transport) as arguments so tests wire fakes and skip the scheduler, while
the default production build uses the live Trendyol store, a JSON repo, and FCM
(or its logging stub when no credentials are present).
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..models import Product
from ..notify import PushNotifier, Transport
from ..pricing import DropRule
from ..stores.base import StoreAdapter
from .poller import poll_all
from .repo import Repo
from .serial import product_from_dict, product_to_dict

log = logging.getLogger("indirimde.server")

DEFAULT_DATA = os.environ.get("INDIRIMDE_DATA", "data/indirimde.json")
DEFAULT_POLL_SECONDS = int(os.environ.get("INDIRIMDE_POLL_SECONDS", "10800"))


# ---- request / response shapes ------------------------------------------
class SearchIn(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=50)


class DeviceIn(BaseModel):
    userId: str
    token: str


class ProductIn(BaseModel):
    store: str
    storeId: str
    name: str
    url: str
    saleMinor: int
    currency: str = "TL"
    wasMinor: Optional[int] = None
    brand: str = ""
    image: str = ""
    rating: Optional[float] = None
    ratingCount: int = 0


class WatchIn(BaseModel):
    userId: str
    product: ProductIn
    minPct: Optional[str] = None
    minMinor: Optional[int] = None


class WatchDelete(BaseModel):
    userId: str
    key: str


def _api_product(p: Product) -> dict:
    d = product_to_dict(p)
    d["key"] = p.key
    d["saleText"] = p.price.sale.format()
    d["wasText"] = p.price.was.format() if p.price.was is not None else None
    return d


def _rule_from(min_pct: Optional[str], min_minor: Optional[int]) -> DropRule:
    kwargs = {}
    if min_pct is not None:
        try:
            kwargs["min_pct"] = Decimal(str(min_pct))
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=400, detail="minPct is not a number")
    if min_minor is not None:
        kwargs["min_minor"] = int(min_minor)
    try:
        return DropRule(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _default_store() -> StoreAdapter:
    from ..stores.trendyol import TrendyolStore
    from ..stores.trendyol_fetch import make_fetchers

    return TrendyolStore(*make_fetchers())


def create_app(
    store: Optional[StoreAdapter] = None,
    repo: Optional[Repo] = None,
    transport: Optional[Transport] = None,
    poll_seconds: Optional[int] = None,
    start_scheduler: bool = True,
) -> FastAPI:
    repo = repo or Repo(DEFAULT_DATA)
    store = store or _default_store()
    if transport is None:
        from .fcm import make_transport

        transport, status = make_transport()
        log.info("FCM transport: %s", status)
    notifier = PushNotifier(transport=transport, tokens=repo.tokens_for)
    interval = poll_seconds if poll_seconds is not None else DEFAULT_POLL_SECONDS

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task: Optional[asyncio.Task] = None
        if start_scheduler:

            async def loop() -> None:
                while True:
                    await asyncio.sleep(interval)
                    try:
                        summary = await asyncio.to_thread(
                            poll_all, repo, store, notifier
                        )
                        log.info("poll cycle: %s", summary)
                    except Exception:
                        log.exception("poll cycle failed")

            task = asyncio.create_task(loop())
        try:
            yield
        finally:
            if task is not None:
                task.cancel()

    app = FastAPI(title="indirimde", version="1.0", lifespan=lifespan)
    # Collaborators live on the app so manual endpoints and tests can reach them.
    app.state.repo = repo
    app.state.store = store
    app.state.notifier = notifier

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "pollSeconds": interval}

    @app.post("/search")
    def search(body: SearchIn) -> dict:
        products = store.search(body.query, limit=body.limit)
        return {"products": [_api_product(p) for p in products]}

    @app.post("/devices")
    def register_device(body: DeviceIn) -> dict:
        repo.register_device(body.userId, body.token)
        return {"ok": True}

    @app.delete("/devices")
    def unregister_device(body: DeviceIn) -> dict:
        repo.unregister_device(body.userId, body.token)
        return {"ok": True}

    @app.get("/watches")
    def list_watches(userId: str) -> dict:
        out = []
        for w in repo.list_watches(userId):
            item = _api_product(w.product)
            item["minPct"] = str(w.rule.min_pct)
            item["minMinor"] = w.rule.min_minor
            item["lastSeenMinor"] = None if w.last_seen is None else w.last_seen.minor
            out.append(item)
        return {"watches": out}

    @app.post("/watches")
    def add_watch(body: WatchIn) -> dict:
        product = product_from_dict(body.product.model_dump())
        rule = _rule_from(body.minPct, body.minMinor)
        # The price the user saw becomes the baseline, so the next poll can
        # already detect a fall against it.
        repo.upsert_watch(body.userId, product, rule, baseline=product.price.sale)
        return {"ok": True, "key": product.key}

    @app.delete("/watches")
    def remove_watch(body: WatchDelete) -> dict:
        removed = repo.remove_watch(body.userId, body.key)
        if not removed:
            raise HTTPException(status_code=404, detail="watch not found")
        return {"ok": True}

    @app.post("/poll")
    async def poll_now() -> dict:
        summary = await asyncio.to_thread(poll_all, repo, store, notifier)
        return summary.__dict__

    return app


# Module-level app for `uvicorn indirimde.server.app:app`.
def _build_default() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    return create_app()


app = None  # built on demand by run.py / uvicorn factory below


def factory() -> FastAPI:
    """Factory for `uvicorn --factory indirimde.server.app:factory`."""
    return _build_default()
