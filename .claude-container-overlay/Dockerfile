# 2026-09-09: Nix with flakes via the Determinate Systems installer.
# Runs as root at build time. --init none skips the systemd daemon (no place in
# a container); build-users-group is cleared so builds run as the calling user
# (no nixbld group); sandbox is off because the container can't set up
# unprivileged build-sandbox user namespaces.
RUN curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix \
        -o /tmp/nix-installer.sh \
    && sh /tmp/nix-installer.sh install linux \
        --init none \
        --no-confirm \
        --extra-conf "experimental-features = nix-command flakes" \
        --extra-conf "build-users-group =" \
        --extra-conf "sandbox = false" \
    && rm /tmp/nix-installer.sh
ENV PATH=/nix/var/nix/profiles/default/bin:$PATH

# 2026-09-09: runtime-user gotcha. The runtime user is created at start with a
# host-mapped UID that doesn't exist at build time, so we can't chown to it.
# Daemon-less Nix run by that user EPERMs trying to chmod root-owned per-user
# dirs, which blocks every `nix` call. Make the store writable by any UID and
# delete the per-user dirs; Nix recreates and owns them on first use.
#
# BUT: /nix/var/nix/profiles/default is a symlink *through* per-user
# (default -> per-user/root/profile -> ...-user-environment). Deleting per-user
# orphans it, so PATH=.../default/bin is dangling and `nix` vanishes from PATH.
# Fix: resolve default to its real store env and re-point it directly (no
# hardcoded hash) BEFORE deleting per-user, so it survives the deletion.
RUN target="$(readlink -f /nix/var/nix/profiles/default)" \
    && rm -f /nix/var/nix/profiles/default \
    && ln -s "$target" /nix/var/nix/profiles/default \
    && chmod -R go+rwX /nix \
    && rm -rf /nix/var/nix/profiles/per-user /nix/var/nix/gcroots/per-user
