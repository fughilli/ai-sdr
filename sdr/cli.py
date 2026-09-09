"""Shared command line for every flowgraph binary.

A flowgraph module defines ``build(args) -> gr.top_block`` and calls
``cli.run(build, "<description>")`` in ``__main__``. This module owns the common
options (source, tuning, gains, mode, output) so every graph behaves the same and
gains new capabilities in one place.
"""

import argparse
import sys

import sdr.gnuradio_env  # noqa: F401

from sdr import runner


def base_parser(description, add_args=None):
    p = argparse.ArgumentParser(description=description)

    mode = p.add_argument_group("collection mode")
    mode.add_argument(
        "--mode",
        choices=["oneshot", "continuous"],
        default="oneshot",
        help="oneshot: run --duration seconds; continuous: run until SIGINT/SIGTERM",
    )
    mode.add_argument("--duration", type=float, default=10.0, help="oneshot length, seconds")

    tune = p.add_argument_group("tuning")
    tune.add_argument(
        "--source",
        choices=["osmosdr", "sim"],
        default="osmosdr",
        help="osmosdr: a real SDR (pick which via --device); sim: hardware-free generator",
    )
    tune.add_argument("--freq", type=float, default=2.44e9, help="center frequency, Hz")
    tune.add_argument("--samp-rate", type=float, default=8e6, dest="samp_rate", help="sample rate, Sps")
    tune.add_argument("--bandwidth", type=float, default=0.0, help="baseband filter BW, Hz (0=track samp-rate)")
    tune.add_argument("--antenna", default="", help="osmosdr antenna name (device-dependent)")
    tune.add_argument(
        "--device",
        default="hackrf=0",
        help="osmosdr device args, e.g. hackrf=0 (tested), rtl=0, bladerf=0, airspy=0, uhd",
    )

    gains = p.add_argument_group("SDR front-end gains via osmosdr (ignored for --source sim)")
    gains.add_argument("--rf-gain", type=float, default=14.0, dest="rf_gain", help="RF/amp stage, dB (HackRF: 0 or 14)")
    gains.add_argument("--if-gain", type=float, default=24.0, dest="if_gain", help="IF/LNA stage, dB (HackRF: 0..40 / 8)")
    gains.add_argument("--bb-gain", type=float, default=20.0, dest="bb_gain", help="BB/VGA stage, dB (HackRF: 0..62 / 2)")

    out = p.add_argument_group("output")
    out.add_argument(
        "--output",
        default="null",
        help="sink spec: null | stdout | file:/p | fifo:/p | udp:host:port",
    )

    p.add_argument("--config", help="YAML file of defaults (keys = long option names, e.g. samp_rate)")

    if add_args is not None:
        add_args(p)
    return p


def _apply_config(parser):
    """Two-pass parse so a --config YAML file can set defaults for everything else."""
    pre, _ = parser.parse_known_args()
    if pre.config:
        import yaml  # pip dep, managed by rules_uv

        with open(pre.config) as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            parser.error("--config %s must contain a YAML mapping" % pre.config)
        parser.set_defaults(**data)
    return parser.parse_args()


def run(build_top_block, description, add_args=None):
    """Parse args, build the graph, and run it in the selected mode."""
    parser = base_parser(description, add_args=add_args)
    args = _apply_config(parser)

    top_block = build_top_block(args)

    if args.mode == "oneshot":
        print(
            "[ai-sdr] oneshot: %s source, %.6g Hz, %.6g Sps, %.1fs -> %s"
            % (args.source, args.freq, args.samp_rate, args.duration, args.output),
            file=sys.stderr,
            flush=True,
        )
        runner.run(top_block, duration=args.duration)
    else:
        print(
            "[ai-sdr] continuous: %s source, %.6g Hz, %.6g Sps -> %s  (Ctrl-C to stop)"
            % (args.source, args.freq, args.samp_rate, args.output),
            file=sys.stderr,
            flush=True,
        )
        runner.run(top_block, duration=None)
