"""Store adapters: the only code that reaches the outside world.

Each store splits in two. The *parser* is pure — it turns a response the store
already gave us into `Product`s and is covered by tests against a captured
fixture. The *fetcher* is the fragile half that actually goes and gets that
response; it lives behind the same interface and fails closed, returning
nothing when a store blocks us or changes its markup, so the rest of the app
never has to guess a price.
"""

from .base import StoreAdapter, STORES, get_store

__all__ = ["StoreAdapter", "STORES", "get_store"]
