"""Utilities for interacting with the host container runtime."""

import os
import shutil
import stat
from urllib.parse import urlparse


def _socket_is_rw(path: str) -> bool:
    """Return True when path exists, is a socket, and is readable/writable."""
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return False

    can_read = os.access(path, os.R_OK)
    can_write = os.access(path, os.W_OK)
    is_sock = stat.S_ISSOCK(st.st_mode)
    return is_sock and can_read and can_write


def has_docker_socket_access(default_socket: str = "/var/run/docker.sock") -> bool:
    """Return True if the process can reach a Docker/Podman daemon.

    Args:
        default_socket: Fallback socket path to probe when env vars are absent.
    """

    # Ensure a container client exists; ramalama checks for docker/podman binaries.
    has_client = shutil.which("docker") or shutil.which("podman")
    if not has_client:
        return False

    # If DOCKER_HOST is set, honor it (supports unix://, tcp://, etc.)
    docker_host = os.getenv("DOCKER_HOST")
    if docker_host:
        parsed = urlparse(docker_host)
        if parsed.scheme == "unix" and parsed.path:
            return _socket_is_rw(parsed.path)
        # For tcp/https/npipe, assume reachable if client exists.
        return True

    # Allow explicit override for the mounted socket path.
    socket_path = os.getenv("DOCKER_SOCKET_PATH", default_socket)

    # Common fallbacks for rootless/podman
    uid = os.getuid() if hasattr(os, "getuid") else 1000
    candidates = [
        socket_path,
        "/run/docker.sock",
        f"/run/user/{uid}/docker.sock",
        "/run/podman/podman.sock",
        f"/run/user/{uid}/podman/podman.sock",
    ]

    return any(_socket_is_rw(path) for path in candidates)
