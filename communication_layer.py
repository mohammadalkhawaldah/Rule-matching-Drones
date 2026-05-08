import json
import socket
import struct
from dataclasses import dataclass
from typing import Any, Dict


TASK_MCAST_GRP = "239.255.0.2"
TASK_MCAST_PORT = 30002
PEER_MCAST_GRP = "239.255.0.1"
PEER_MCAST_PORT = 30001
MCAST_TTL = 1


@dataclass(frozen=True)
class DroneControlEndpoint:
    drone_id: str
    system_id: int
    grpc_host: str
    grpc_port: int
    system_address: str
    home_lat_deg: float
    home_lon_deg: float
    home_alt_m: float

    @property
    def grpc_uri(self) -> str:
        return f"grpc://{self.grpc_host}:{self.grpc_port}"


CONTROL_ENDPOINTS: Dict[str, DroneControlEndpoint] = {
    "drone_1": DroneControlEndpoint("drone_1", 1, "127.0.0.1", 50040, "tcp://127.0.0.1:5760", -35.363262, 149.165237, 584.0),
    "drone_2": DroneControlEndpoint("drone_2", 2, "127.0.0.1", 50041, "tcp://127.0.0.1:5770", -35.364262, 149.166237, 584.0),
    "drone_3": DroneControlEndpoint("drone_3", 3, "127.0.0.1", 50042, "tcp://127.0.0.1:5780", -35.365262, 149.167237, 584.0),
    "drone_4": DroneControlEndpoint("drone_4", 4, "127.0.0.1", 50043, "tcp://127.0.0.1:5790", -35.366262, 149.168237, 584.0),
    "drone_5": DroneControlEndpoint("drone_5", 5, "127.0.0.1", 50044, "tcp://127.0.0.1:5800", -35.367262, 149.169237, 584.0),
    "drone_6": DroneControlEndpoint("drone_6", 6, "127.0.0.1", 50045, "tcp://127.0.0.1:5810", -35.368262, 149.170237, 584.0),
}


def make_multicast_tx_socket(ttl: int = MCAST_TTL) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    return sock


def make_multicast_rx_socket(group: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except OSError:
        pass
    sock.bind(("", port))
    membership = struct.pack("4sl", socket.inet_aton(group), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    return sock


def send_multicast_json(payload: Dict[str, Any], group: str, port: int) -> None:
    sock = make_multicast_tx_socket()
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), (group, port))
    finally:
        sock.close()
