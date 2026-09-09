"""Streaming power spectrum of the tuned band: FFT magnitude frames to any sink.

Each output frame is ``--fft-size`` float32 bins of |FFT|^2 (linear power),
DC-centered. Point ``--freq``/``--samp-rate`` at the slice of spectrum you care
about (e.g. a BLE advertising channel) and read the frames back for a waterfall,
a channel-occupancy detector, etc.

Examples:
    # 5 s of 1024-bin spectra around 2.44 GHz to a file
    bazel run //graphs:power_scan -- --duration 5 --output file:/tmp/psd.f32

    # continuous spectra over UDP (sim source, no radio needed)
    bazel run //graphs:power_scan -- --source sim --mode continuous \\
        --output udp:127.0.0.1:5001
"""

import sdr.gnuradio_env  # noqa: F401

from gnuradio import blocks, fft, gr
from gnuradio.fft import window

from sdr import cli, sinks, sources


class PowerScan(gr.top_block):
    def __init__(self, args):
        gr.top_block.__init__(self, "power_scan")
        n = args.fft_size

        source = sources.build_source(args)
        to_vec = blocks.stream_to_vector(gr.sizeof_gr_complex, n)
        # keep 1 of every `decim` frames so we don't emit millions/sec
        keep = blocks.keep_one_in_n(gr.sizeof_gr_complex * n, max(args.decim, 1))
        xform = fft.fft_vcc(n, True, window.blackmanharris(n), True, 1)
        mag = blocks.complex_to_mag_squared(n)
        sink = sinks.build_sink(args.output, gr.sizeof_float * n)

        self.connect(source, to_vec, keep, xform, mag, sink)


def _add_args(p):
    grp = p.add_argument_group("power_scan")
    grp.add_argument("--fft-size", type=int, default=1024, dest="fft_size")
    grp.add_argument("--decim", type=int, default=100, help="emit 1 of every N FFT frames")


if __name__ == "__main__":
    cli.run(PowerScan, "Streaming FFT power spectrum of the tuned band", add_args=_add_args)
