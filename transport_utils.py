def normalize_mavsdk_system_address(system_address: str) -> str:
    """
    Convert legacy MAVSDK transport URLs to the explicit current scheme.

    The launcher and operator still accept the older tcp:// form from the
    existing runbook, but MAVSDK now emits a deprecation warning for it.
    """

    address = system_address.strip()
    if address.startswith("tcp://"):
        return "tcpout://" + address[len("tcp://") :]
    if address.startswith("udp://"):
        return "udpout://" + address[len("udp://") :]
    return address
