{
  description = "GNU Radio processing environment for 2.4 GHz SDR snooping with a HackRF One";

  # Pinned to the NixOS 25.05 release, which ships the latest GNU Radio release
  # (3.10.12.0) built against Python 3.11 -- see the decision log in README.md.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };

          # GNU Radio wrapped with the osmocom source block (gr-osmosdr). osmosdr
          # links libhackrf directly, so the HackRF One works with no extra Soapy
          # plugin path wiring. Add more out-of-tree blocks to this list as needed.
          gnuradio = pkgs.gnuradio.override {
            extraPackages = [ pkgs.gnuradioPackages.osmosdr ];
          };
        in
        rec {
          # A self-contained Python 3.11 interpreter + site-packages that can
          # `import gnuradio` and `import osmosdr`. Bazel imports THIS derivation's
          # site-packages onto sys.path (see //nix:grenv.bzl).
          grenv = gnuradio.pythonEnv;
          default = grenv;

          # Host-side CLI tools for `nix run .#hackrf -- ...` (hackrf_info, etc.).
          inherit (pkgs) hackrf soapyhackrf;

          # The unwrapped, fully-wrapped GNU Radio (gnuradio-companion, gr_modtool).
          inherit gnuradio;
        });

      devShells = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = [
              self.packages.${system}.grenv
              pkgs.hackrf
            ];
            shellHook = ''
              echo "GNU Radio $(python -c 'import gnuradio; print(gnuradio.__path__[0])' 2>/dev/null && gnuradio-config-info --version 2>/dev/null)"
            '';
          };
        });
    };
}
