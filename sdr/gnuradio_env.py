"""Import for its side effect: put the Nix-built GNU Radio onto ``sys.path``.

Usage (must come *before* any ``gnuradio``/``osmosdr`` import in the module)::

    import sdr.gnuradio_env  # noqa: F401
    from gnuradio import gr, blocks

GNU Radio, gr-osmosdr, and their numpy are provided by the Nix env built in
``//nix:grenv.bzl`` and are inserted at the *front* of ``sys.path`` so their
(ABI-matched) numpy wins over any pip-provided one.
"""

import os
import sys

try:
    from grenv_path import PREFIX, SITE_PACKAGES
except ImportError as exc:  # pragma: no cover - only happens outside Bazel
    raise ImportError(
        "grenv_path is missing. GNU Radio flowgraphs must be built with Bazel and "
        "depend on //sdr:sdr (which pulls in @grenv). If you are running this file "
        "directly, run it through its gr_py_binary target instead."
    ) from exc


def activate():
    """Idempotently make ``import gnuradio`` / ``import osmosdr`` work."""
    if SITE_PACKAGES not in sys.path:
        sys.path.insert(0, SITE_PACKAGES)
    # GNU Radio reads prefs/blocks relative to its prefix; point at the Nix env.
    os.environ.setdefault("GR_PREFIX", PREFIX)


activate()
