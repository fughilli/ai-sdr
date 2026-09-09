"""Output sinks selected by a small spec string, for both collection modes.

Spec grammar (``--output``):
    ``null``              discard (default; good for smoke tests)
    ``stdout`` or ``-``   write raw bytes to fd 1 (pipe into another process)
    ``file:/path``        write to a file (a bare ``/path`` also works)
    ``fifo:/path``        create+write a named pipe (a reader must drain it)
    ``udp:host:port``     stream datagrams (host optional -> 127.0.0.1)

Every sink is byte-oriented over ``itemsize``, so the same specs work for complex
IQ streams and for vector streams (e.g. FFT frames) alike.
"""

import os

import sdr.gnuradio_env  # noqa: F401

from gnuradio import blocks, gr, network

_UDP_PAYLOAD = 1472  # bytes; fits a datagram under a 1500-byte Ethernet MTU
_UDP_HEADER_NONE = 0  # raw stream, no per-packet sequence header


def _ensure_fifo(path):
    import stat

    if os.path.exists(path):
        if not stat.S_ISFIFO(os.stat(path).st_mode):
            raise ValueError("fifo path exists and is not a FIFO: %s" % path)
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    os.mkfifo(path)


def build_sink(spec, itemsize=None):
    """Return a GNU Radio sink block for ``spec``.

    ``itemsize`` defaults to one ``gr_complex`` (raw IQ). Pass e.g.
    ``gr.sizeof_float * fft_size`` for vector streams.
    """
    if itemsize is None:
        itemsize = gr.sizeof_gr_complex

    if spec in ("-", "stdout"):
        return blocks.file_descriptor_sink(itemsize, 1)

    if spec in ("null", "/dev/null"):
        return blocks.null_sink(itemsize)

    scheme, sep, rest = spec.partition(":")

    if scheme == "udp" and sep:
        # GNU Radio 3.10 moved UDP into gr-network; each item is sent whole
        # (veclen=1), so vector streams (e.g. FFT frames) go out one frame/packet.
        host, _, port = rest.rpartition(":")
        return network.udp_sink(
            itemsize, 1, host or "127.0.0.1", int(port), _UDP_HEADER_NONE, _UDP_PAYLOAD, True
        )

    if scheme == "fifo" and sep:
        _ensure_fifo(rest)
        return blocks.file_sink(itemsize, rest, False)

    path = rest if (scheme == "file" and sep) else spec
    sink = blocks.file_sink(itemsize, path, False)
    sink.set_unbuffered(False)
    return sink
