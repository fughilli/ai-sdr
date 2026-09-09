"""Capture raw complex IQ from any tuned band to any sink.

Examples:
    # 10 s of IQ at 2.44 GHz, 8 Msps, to a file (default device: hackrf=0)
    bazel run //graphs:iq_capture -- --freq 2.44e9 --output file:/tmp/cap.cfile

    # a different radio + band: FM broadcast off an RTL-SDR
    bazel run //graphs:iq_capture -- --device rtl=0 --freq 100e6 --samp-rate 2.4e6 \\
        --output file:/tmp/fm.cfile

    # stream forever to another host over UDP until Ctrl-C
    bazel run //graphs:iq_capture -- --mode continuous \\
        --freq 2.402e9 --samp-rate 20e6 --output udp:10.0.0.5:5000

    # no radio? prove the graph runs with the simulator
    bazel run //graphs:iq_capture -- --source sim --output file:/tmp/sim.cfile

Output is interleaved 32-bit float I/Q (GNU Radio's native ``complex64`` /
``.cfile`` format).
"""

import sdr.gnuradio_env  # noqa: F401  (must precede any gnuradio import)

from gnuradio import gr

from sdr import cli, sinks, sources


class IQCapture(gr.top_block):
    def __init__(self, args):
        gr.top_block.__init__(self, "iq_capture")
        source = sources.build_source(args)
        sink = sinks.build_sink(args.output, gr.sizeof_gr_complex)
        self.connect(source, sink)


if __name__ == "__main__":
    cli.run(IQCapture, "Capture raw IQ from any tuned band to a file/FIFO/UDP sink")
