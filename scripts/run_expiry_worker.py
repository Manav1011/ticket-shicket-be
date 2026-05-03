#!/usr/bin/env python3
"""Entry point for expiry worker — run via systemd/supervisor."""
import asyncio
import logging
from apps.queues.workers.expiry import main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    asyncio.run(main())
