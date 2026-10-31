"""indirimde — price-watch backend.

The package is split so the fragile parts stay isolated from the parts we can
trust. Everything in `money` and `pricing` is pure: given the same input it
returns the same output, touches no network, and is covered by tests against
captured store responses. The store adapters under `stores/` are the only place
that talks to the outside world, and they fail closed: when a price cannot be
read, they return nothing rather than guessing.
"""
