from network import MessengerServer
import signal
import sys

def signal_handler(sig, frame):
    print("\nShutting down server...")
    if server:
        server.running = False
        server.close()
    sys.exit(0)

if __name__ == "__main__":
    server = None
    try:
        signal.signal(signal.SIGINT, signal_handler)
        server = MessengerServer()
        server.start()
    except Exception as e:
        print(f"Server failed to start: {str(e)}")
        if server:
            server.close()
        sys.exit(1)