"""Hardware-free smoke test: build the sim flowgraph and run it briefly.

Proves the whole stack loads and executes without a radio -- the Nix GNU Radio
imports under the rules_python interpreter, a graph assembles, runs, and stops
cleanly. Exits non-zero on any failure, so it works as a plain `py_test`.
"""

import os
import tempfile

import sdr.gnuradio_env  # noqa: F401

from gnuradio import gr

from sdr import runner, sinks, sources


def test_sim_capture_to_file():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "out.cfile")
        tb = gr.top_block("smoke")
        src = sources.SimSource(200e3)
        sink = sinks.build_sink("file:" + path, gr.sizeof_gr_complex)
        tb.connect(src, sink)
        runner.run(tb, duration=0.3)
        assert os.path.getsize(path) > 0, "expected some IQ samples on disk"


def test_null_and_udp_sinks_build():
    assert sinks.build_sink("null") is not None
    assert sinks.build_sink("udp:127.0.0.1:9999", gr.sizeof_gr_complex) is not None


if __name__ == "__main__":
    test_sim_capture_to_file()
    test_null_and_udp_sinks_build()
    print("ok")
