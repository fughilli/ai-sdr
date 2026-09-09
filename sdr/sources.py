"""Signal sources: real SDRs (via gr-osmosdr) and a hardware-free simulator.

Real radios are driven through **gr-osmosdr**, which supports many devices behind
one API -- RTL-SDR, HackRF, bladeRF, Airspy, USRP, and more -- selected by the
``--device`` string (e.g. ``hackrf=0``, ``rtl=0``, ``bladerf=0``). The **HackRF
One** is the device this project is currently tested against.

The simulator lets flowgraphs build, run, and be tested headless with no radio
attached -- essential for CI and for verifying a graph before pointing it at the
air. Both sources present a single complex (``gr_complex``) output.
"""

import sdr.gnuradio_env  # noqa: F401  (puts GNU Radio on sys.path)

from gnuradio import analog, blocks, gr

# Default front-end gains. These map onto the osmosdr gain stages; not every
# device exposes all three (a device ignores stages it lacks). For the HackRF One:
#   RF (set_gain)    : front-end amp, 0 or 14 dB
#   IF (set_if_gain) : LNA,  0..40 dB in 8 dB steps
#   BB (set_bb_gain) : VGA,  0..62 dB in 2 dB steps
DEFAULT_RF_GAIN = 14.0
DEFAULT_IF_GAIN = 24.0
DEFAULT_BB_GAIN = 20.0


def osmosdr_source(
    samp_rate,
    center_freq,
    *,
    rf_gain=DEFAULT_RF_GAIN,
    if_gain=DEFAULT_IF_GAIN,
    bb_gain=DEFAULT_BB_GAIN,
    bandwidth=0.0,
    antenna="",
    device="hackrf=0",
):
    """An ``osmosdr.source`` bound to the radio named by ``device``.

    ``bandwidth=0`` lets the baseband filter track the sample rate.
    """
    import osmosdr  # imported lazily so `import sdr.sources` works without a radio

    src = osmosdr.source(args=device)
    src.set_sample_rate(samp_rate)
    src.set_center_freq(center_freq, 0)
    src.set_freq_corr(0, 0)
    src.set_gain_mode(False, 0)  # manual gain
    src.set_gain(rf_gain, 0)
    src.set_if_gain(if_gain, 0)
    src.set_bb_gain(bb_gain, 0)
    src.set_bandwidth(bandwidth or samp_rate, 0)
    if antenna:
        src.set_antenna(antenna, 0)
    return src


class SimSource(gr.hier_block2):
    """A throttled complex tone + Gaussian noise, standing in for a real radio.

    Throttling to ``samp_rate`` makes ``--mode continuous`` and ``--duration``
    behave in real time exactly as they would against hardware (a real SDR
    provides its own timing; this block supplies it for the simulator).
    """

    def __init__(self, samp_rate, tone_hz=100e3, amplitude=0.5, noise_amp=0.05):
        gr.hier_block2.__init__(
            self,
            "SimSource",
            gr.io_signature(0, 0, 0),
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
        )
        tone = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, tone_hz, amplitude)
        noise = analog.noise_source_c(analog.GR_GAUSSIAN, noise_amp, 0)
        adder = blocks.add_cc()
        throttle = blocks.throttle(gr.sizeof_gr_complex, samp_rate, True)
        self.connect(tone, (adder, 0))
        self.connect(noise, (adder, 1))
        self.connect(adder, throttle, self)


def build_source(args):
    """Construct the source selected by the shared CLI (``--source``)."""
    if args.source == "sim":
        return SimSource(args.samp_rate)
    return osmosdr_source(
        args.samp_rate,
        args.freq,
        rf_gain=args.rf_gain,
        if_gain=args.if_gain,
        bb_gain=args.bb_gain,
        bandwidth=args.bandwidth,
        antenna=args.antenna,
        device=args.device,
    )
