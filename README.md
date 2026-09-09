# ai-sdr

A general interface for **AIs/agents to drive software-defined radios**. Describe
DSP as a **GNU Radio** flowgraph in Python, and run it **headless** to capture and
process signals — from any radio, on any band, to any output. 2.4 GHz snooping
with a HackRF One is one thing you can do with it, not the boundary of it.

- **GNU Radio comes from Nix** (latest release, 3.10.12.0), pinned in a flake.
- **Flowgraphs are `py_binary` targets** — describe the DSP in Python, `bazel run`
  it. GNU Radio is layered onto the interpreter's `sys.path` at runtime.
- **Two collection modes, one CLI**: `oneshot` (run for `--duration` seconds) and
  `continuous` (run until Ctrl-C / SIGTERM).
- **Pluggable outputs**: file, named pipe (FIFO), UDP socket, stdout, or null.
- **Python via `rules_python`, deps via `rules_uv`** (hermetic, lockfile-driven).

```
bazel run //graphs:iq_capture -- --freq 100e6 --device rtl=0 --output file:/tmp/fm.cfile --duration 5
bazel run //graphs:power_scan -- --freq 2.44e9 --mode continuous --output udp:127.0.0.1:5001
```

---

## Supported hardware

Real radios are driven through **gr-osmosdr**, so anything it supports works in
principle — RTL-SDR, HackRF, bladeRF, Airspy, USRP (UHD), and more — selected by
the `--device` string:

| Device | `--device` | Status |
| --- | --- | --- |
| HackRF One | `hackrf=0` (default) | **tested** |
| RTL-SDR | `rtl=0` | supported via osmosdr, untested here |
| bladeRF | `bladerf=0` | supported via osmosdr, untested here |
| Airspy | `airspy=0` | supported via osmosdr, untested here |
| USRP | `uhd` | supported via osmosdr, untested here |
| *(none)* | `--source sim` | built-in tone+noise generator, no radio |

"Tested" means exercised on real hardware in this project; the others are exposed
by the same osmosdr source and should work once you point `--device` at them —
please report back. Adding a non-osmosdr backend (e.g. SoapySDR) is a matter of
adding one function in `sdr/sources.py` and a `--source` choice.

## Requirements

- **Bazel** via Bazelisk (pinned to 8.3.1 by `.bazelversion`; nothing else system-wide).
- **Nix** with flakes, on `PATH`. The flowgraph targets build GNU Radio from the
  flake the first time they're fetched. (Non-flowgraph targets — e.g. the lockfile
  generator — build without Nix.)
- **An SDR** for live capture. Without one, use `--source sim` to exercise any
  graph end-to-end.

If your radio is HackRF-family, check it from the pinned tools:

```
nix shell .#hackrf -c hackrf_info
```

## Quick start

```bash
# 1. (once) generate the pip lockfile if you change requirements.in
bazel run //:generate_requirements_lock

# 2. prove the toolchain works with no radio attached
bazel test //tests:smoke_test

# 3. capture 10 s of raw IQ to a file (default device: hackrf=0)
bazel run //graphs:iq_capture -- --freq 2.44e9 --samp-rate 8e6 \
    --output file:/tmp/cap.cfile --duration 10

# 4. stream a live power spectrum until you Ctrl-C
bazel run //graphs:power_scan -- --mode continuous \
    --freq 2.44e9 --samp-rate 20e6 --fft-size 2048 --output udp:127.0.0.1:5001
```

## The shared CLI

Every flowgraph binary understands the same options (see `sdr/cli.py`):

| Option | Default | Meaning |
| --- | --- | --- |
| `--mode` | `oneshot` | `oneshot` (fixed length) or `continuous` (until signal) |
| `--duration` | `10` | oneshot length, seconds |
| `--source` | `osmosdr` | `osmosdr` (a real SDR, pick via `--device`) or `sim` (no hardware) |
| `--device` | `hackrf=0` | osmosdr device args (e.g. `hackrf=0`, `rtl=0`, `bladerf=0`, `uhd`) |
| `--freq` | `2.44e9` | center frequency, Hz |
| `--samp-rate` | `8e6` | sample rate, Sps |
| `--bandwidth` | `0` | baseband filter BW (0 = track sample rate) |
| `--rf-gain` / `--if-gain` / `--bb-gain` | `14/24/20` | osmosdr gain stages, dB (HackRF: amp / LNA / VGA) |
| `--antenna` | — | osmosdr antenna name (device-dependent) |
| `--output` | `null` | sink spec (below) |
| `--config` | — | YAML file of defaults (keys = option names, e.g. `samp_rate: 20e6`) |

### Output specs (`--output`)

| Spec | Sink |
| --- | --- |
| `null` | discard (default) |
| `stdout` or `-` | raw bytes to fd 1 (pipe into another process) |
| `file:/path` (or bare `/path`) | write to file (IQ is `complex64` — GNU Radio `.cfile`) |
| `fifo:/path` | create + write a named pipe (a reader must drain it) |
| `udp:host:port` | UDP datagrams (`host` optional → 127.0.0.1) |

`continuous` mode stops cleanly on SIGINT/SIGTERM, always flushing the sink and
releasing the radio.

## Writing a new flowgraph

Describe the graph in Python and wrap it with `gr_py_binary`:

```python
# graphs/my_graph.py
import sdr.gnuradio_env            # noqa: F401  (must precede gnuradio imports)
from gnuradio import gr
from sdr import cli, sinks, sources

class MyGraph(gr.top_block):
    def __init__(self, args):
        gr.top_block.__init__(self, "my_graph")
        src = sources.build_source(args)         # osmosdr or sim, per --source
        sink = sinks.build_sink(args.output, gr.sizeof_gr_complex)
        self.connect(src, sink)                  # ... your DSP in between

if __name__ == "__main__":
    cli.run(MyGraph, "what this graph does")
```

```python
# graphs/BUILD.bazel
load("//sdr:defs.bzl", "gr_py_binary")
gr_py_binary(name = "my_graph", srcs = ["my_graph.py"])
```

Add per-graph options with `cli.run(..., add_args=fn)` where `fn(parser)` calls
`parser.add_argument(...)` (see `graphs/power_scan.py`). To add a new radio
backend, add a function to `sdr/sources.py` and a `--source` choice in `sdr/cli.py`.

## Layout

```
flake.nix / flake.lock   GNU Radio (+ gr-osmosdr) env, pinned to nixpkgs 25.05
nix/grenv.bzl            module extension: `nix build .#grenv`, expose to Bazel
MODULE.bazel             rules_python (3.11) + rules_uv + the @grenv extension
requirements.in/.lock    pip deps (rules_uv); regen: //:generate_requirements_lock
sdr/                     framework: gnuradio_env, sources, sinks, runner, cli, defs.bzl
graphs/                  example flowgraphs (iq_capture, power_scan)
tests/                   hardware-free smoke test
```

## How GNU Radio reaches Python (the Nix ↔ Bazel bridge)

`//nix:grenv.bzl` is a module extension whose repository rule runs
`nix build .#grenv` against this repo's flake (pinned by `flake.lock`) and writes
the resulting store path into a generated `grenv_path.py`. `sdr/gnuradio_env.py`
prepends that env's `site-packages` to `sys.path` before any `gnuradio` import.

- The interpreter is **CPython 3.11** (`rules_python`) — the same ABI Nix builds
  GNU Radio's pybind11 modules against, so they import directly.
- GNU Radio's `.so`s carry absolute RPATHs into `/nix/store`, so no multi-gigabyte
  closure is copied into runfiles and no `LD_LIBRARY_PATH` juggling is needed.
- Only the flowgraph/test targets depend on `@grenv`, so they (and only they)
  require `nix`; `//:generate_requirements_lock` builds on a Nix-less machine.

## Decision log

| Date | Decision | Why |
| --- | --- | --- |
| 2026-09-09 | nixpkgs pinned to `nixos-25.05` (`ac62194`) | ships GNU Radio 3.10.12.0 (latest release) built against Python 3.11 |
| 2026-09-09 | rules_python interpreter = 3.11 | must match the Python that Nix builds GNU Radio's C-extensions against |
| 2026-09-09 | Bazel 8.3.1 | rules_python 2.x-era `py_binary` misbehaves on Bazel 7.x; 8.x is clean |
| 2026-09-09 | rules_python 1.4.1, rules_uv 0.86.0 | current, mutually compatible on Bazel 8 |
| 2026-09-09 | GNU Radio via Nix, layered on `sys.path` (not a py toolchain) | keeps the hermetic `rules_python` interpreter + `rules_uv` deps while borrowing the huge GNU Radio closure from Nix |
| 2026-09-09 | radios via gr-osmosdr (HackRF tested) | one API spanning many SDRs; keeps the project device-agnostic |

Bump pins intentionally: edit `flake.nix` + `nix flake update`, or the
`bazel_dep` versions + a build to refresh `MODULE.bazel.lock`, and update this
log in the same change.
