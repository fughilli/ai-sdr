"""`gr_py_binary`: a py_binary that can run GNU Radio flowgraphs headless.

It is a thin wrapper over rules_python's py_binary that always depends on
//sdr:sdr, which in turn pulls in the Nix GNU Radio env (@grenv) and the shared
framework (sources/sinks/runner/cli). Describe a flowgraph in Python and wrap it:

    load("//sdr:defs.bzl", "gr_py_binary")
    gr_py_binary(name = "iq_capture", srcs = ["iq_capture.py"])

Building/running the target requires `nix` on PATH (it fetches @grenv).
"""

load("@rules_python//python:defs.bzl", "py_binary")

def gr_py_binary(name, srcs, main = None, deps = None, **kwargs):
    py_binary(
        name = name,
        srcs = srcs,
        main = main or srcs[0],
        deps = (deps or []) + ["//sdr:sdr"],
        **kwargs
    )
