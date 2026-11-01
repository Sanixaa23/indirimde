"""Run the server: `python -m indirimde.server.run`.

Host, port and poll interval come from the environment so deployment needs no
code change:
  INDIRIMDE_HOST          (default 0.0.0.0)
  INDIRIMDE_PORT          (default 8000)
  INDIRIMDE_POLL_SECONDS  (default 10800 = 3h)
  INDIRIMDE_DATA          (default data/indirimde.json)
  INDIRIMDE_FCM_CREDENTIALS / GOOGLE_APPLICATION_CREDENTIALS  (service account)
"""

from __future__ import annotations

import logging
import os

import uvicorn

from .app import create_app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    uvicorn.run(
        app,
        host=os.environ.get("INDIRIMDE_HOST", "0.0.0.0"),
        port=int(os.environ.get("INDIRIMDE_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
