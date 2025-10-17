# KEYLOGGER-ADVPROG: gRPC Refactor 

**Goal:** Refactoring the client-side log uploader from **REST (HTTP/JSON)** to a high-performance **gRPC (HTTP/2 / Protocol Buffers)** service.

##  Setup

1.  **Install:**
    ```bash
    pip install pynput grpcio grpcio-tools
    ```

2.  **Generate Code:**
    ```bash
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. log_service.proto
    ```

