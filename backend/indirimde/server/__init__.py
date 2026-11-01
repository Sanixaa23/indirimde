"""The server half of indirimde: a FastAPI app plus a background poller.

The app is thin by design. Every decision that matters — is this a real drop,
what does the notification say, is the store reachable — already lives in the
pure core and the store adapters. This package only exposes that over HTTP,
keeps a little durable state (which devices want which products), and runs the
poll loop on a timer.
"""
