#!/usr/bin/env bash
# Opt-in launch only. No packages, permissions, services or VM disks are created.
set -euo pipefail
if [[ $# != 2 || "$1" != "--start-approved-vm" ]]; then
  echo 'Usage: start-vm.sh --start-approved-vm /absolute/path/worker.qcow2' >&2
  exit 2
fi
disk="$2"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# Always measure Windows physical/commit headroom, not the overlapping WSL pool.
# A missing/failed measurement refuses startup. This gate never provisions a disk.
python3 "$script_dir/preflight_vm.py"
[[ "$disk" =~ ^/[A-Za-z0-9_./-]+\.qcow2$ && -f "$disk" && ! -L "$disk" ]] || { echo 'Provide an existing private qcow2 guest disk' >&2; exit 2; }
[[ -r /dev/kvm && -w /dev/kvm ]] || { echo 'KVM is unavailable to this user; no software-emulation fallback' >&2; exit 1; }
command -v qemu-system-x86_64 >/dev/null
# No shared drives, Docker socket, clipboard, guest agent or host devices.
# Phase 1 blocks guest outbound networking; only loopback SSH is forwarded.
exec qemu-system-x86_64 -name agsci-original-worker -enable-kvm -cpu host \
  -smp 4 -m 6144 -drive "file=$disk,if=virtio,format=qcow2" \
  -nic 'user,model=virtio-net-pci,restrict=on,hostfwd=tcp:127.0.0.1:2222-:22' \
  -display none -serial mon:stdio -no-reboot
