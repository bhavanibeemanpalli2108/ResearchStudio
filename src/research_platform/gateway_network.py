"""Prepared QEMU boundary specification. Printing it does not deploy a network."""

from __future__ import annotations

import json

GUEST_GATEWAY = "10.0.2.100"
GATEWAY_PORT = 8843


def destination_allowed(address: str, port: int) -> bool:
    """Expected guest egress policy for local negative tests, not a packet filter."""
    return address == GUEST_GATEWAY and type(port) is int and port == GATEWAY_PORT


def qemu_network_arguments() -> list[str]:
    # All targets/commands are fixed trusted-host configuration. No research
    # request, guest input, real key or arbitrary destination enters this string.
    return [
        "-nic",
        "user,model=virtio-net-pci,restrict=on,"
        "hostfwd=tcp:127.0.0.1:2222-:22,"
        "guestfwd=tcp:10.0.2.100:8843-cmd:/usr/bin/socat STDIO TCP4:127.0.0.1:8843",
    ]


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "qemu_args": qemu_network_arguments(),
                "deployed": False,
                "requires_reviewed_host_socat": True,
                "direct_provider_egress_expected": False,
            }
        )
    )
