#!/usr/bin/env python3
"""
Sentinel Omega — Shutdown
Gracefully stops the running orchestrator by sending SIGTERM to the PID.

Usage:
    python sentinel_omega/shutdown.py
    python sentinel_omega/shutdown.py --force    # SIGKILL if SIGTERM fails
"""

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

PIDFILE = Path(__file__).parent / "data" / "sentinel_omega.pid"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SHUTDOWN] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _read_pid() -> int:
    if not PIDFILE.exists():
        return 0
    try:
        return int(PIDFILE.read_text().strip())
    except (ValueError, OSError):
        return 0


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def shutdown(force: bool = False):
    pid = _read_pid()

    if pid == 0:
        logger.info("No PID file found — Sentinel Omega is not running.")
        sys.exit(0)

    if not _process_alive(pid):
        logger.info(f"PID {pid} is not running (stale pidfile). Cleaning up.")
        PIDFILE.unlink(missing_ok=True)
        sys.exit(0)

    logger.info(f"Sending SIGTERM to Sentinel Omega (PID {pid})...")
    os.kill(pid, signal.SIGTERM)

    for i in range(30):
        time.sleep(1)
        if not _process_alive(pid):
            logger.info(f"Sentinel Omega (PID {pid}) terminated gracefully.")
            PIDFILE.unlink(missing_ok=True)
            return
        if i % 5 == 4:
            logger.info(f"Waiting for shutdown... ({i + 1}s)")

    if force:
        logger.warning(f"SIGTERM timeout — sending SIGKILL to PID {pid}...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(2)
        if not _process_alive(pid):
            logger.info(f"Sentinel Omega (PID {pid}) killed.")
            PIDFILE.unlink(missing_ok=True)
            return
        logger.error(f"Failed to kill PID {pid}.")
        sys.exit(1)
    else:
        logger.warning(
            f"Sentinel Omega (PID {pid}) did not stop within 30s. "
            f"Use --force to send SIGKILL."
        )
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sentinel Omega — Graceful Shutdown",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Send SIGKILL if graceful shutdown times out (30s)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    shutdown(force=args.force)
