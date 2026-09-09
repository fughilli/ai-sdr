"""Drive a GNU Radio ``top_block`` in one of two collection modes.

oneshot     run for a fixed number of seconds, then stop cleanly.
continuous  run until SIGINT (Ctrl-C) or SIGTERM, then stop cleanly.

Both paths always ``stop()`` + ``wait()`` so file/FIFO/UDP sinks flush and the
radio is released, even on signal.
"""

import signal
import sys
import threading
import time

import sdr.gnuradio_env  # noqa: F401


def run(top_block, duration=None, *, on_start=None):
    """Start ``top_block`` and block until done.

    ``duration=None`` runs until a signal arrives (continuous); a numeric
    ``duration`` runs that many seconds, but a signal still stops it early.
    """
    stop_event = threading.Event()

    def _handler(_signum, _frame):
        stop_event.set()

    previous = {sig: signal.signal(sig, _handler) for sig in (signal.SIGINT, signal.SIGTERM)}

    started = time.monotonic()
    top_block.start()
    try:
        if on_start is not None:
            on_start()
        if duration is not None:
            stop_event.wait(duration)
        else:
            while not stop_event.is_set():
                stop_event.wait(0.25)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        top_block.stop()
        top_block.wait()

    elapsed = time.monotonic() - started
    print("[ai-sdr] stopped after %.2fs" % elapsed, file=sys.stderr, flush=True)
