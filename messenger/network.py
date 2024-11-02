import socket
import threading
import zlib
import json
from datetime import datetime
from queue import Queue, Empty
import select
import logging

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

class MessengerClient:
    def __init__(self, username, host='localhost', port=5000):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.username = username
        self.host = host
        self.port = port
        self.on_message = None
        self.running = True
        self.send_queue = Queue()
        self.BUFFER_SIZE = 4096
        self.lock = threading.Lock()

    def connect(self):
        try:
            self.socket.settimeout(5)  # Add connection timeout
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)  # Reset timeout for normal operation
            
            # Start sender thread
            self.sender_thread = threading.Thread(target=self._sender_loop)
            self.sender_thread.daemon = True
            self.sender_thread.start()
            return True
        except (ConnectionRefusedError, socket.timeout) as e:
            logging.error(f"Connection failed: {str(e)}")
            return False

    def _sender_loop(self):
        while self.running:
            try:
                message = self.send_queue.get(timeout=0.1)
                if message:
                    self._send_data(message)
            except Empty:  # Fixed Queue.Empty to Empty
                continue
            except Exception as e:
                if self.running:
                    logging.error(f"Send error: {str(e)}")
                break

    def _send_data(self, data):
        try:
            with self.lock:  # Thread-safe sending
                # Convert to JSON and compress
                json_data = json.dumps(data)
                compressed = zlib.compress(json_data.encode('utf-8'))
                
                # Send length first
                length = len(compressed)
                self.socket.sendall(length.to_bytes(4, byteorder='big'))
                
                # Send compressed data
                self.socket.sendall(compressed)
        except Exception as e:
            raise Exception(f"Send failed: {str(e)}")

    def _receive_data(self):
        try:
            # Receive length first
            length_data = self.socket.recv(4)
            if not length_data or len(length_data) != 4:
                return None
            
            length = int.from_bytes(length_data, byteorder='big')
            if length > 1048576:  # Limit message size to 1MB
                raise ValueError("Message too large")
            
            # Receive data in chunks
            chunks = []
            bytes_received = 0
            while bytes_received < length:
                chunk = self.socket.recv(min(length - bytes_received, self.BUFFER_SIZE))
                if not chunk:
                    return None
                chunks.append(chunk)
                bytes_received += len(chunk)
            
            # Decompress and parse JSON
            compressed_data = b''.join(chunks)
            json_data = zlib.decompress(compressed_data).decode('utf-8')
            return json.loads(json_data)
        except Exception as e:
            logging.error(f"Receive error: {str(e)}")
            return None

    def receive_messages(self):
        while self.running:
            try:
                ready = select.select([self.socket], [], [], 0.1)
                if ready[0]:
                    data = self._receive_data()
                    if not data:
                        break
                    if self.on_message:
                        self.on_message(data['message'])
            except Exception as e:
                if self.running:
                    logging.error(f"Connection lost: {str(e)}")
                break
        self.close()

    def send_message(self, message):
        if not self.running:
            raise Exception("Client is not running")
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            data = {
                'timestamp': timestamp,
                'username': self.username,
                'message': message,
                'type': 'message'
            }
            self.send_queue.put(data)
        except Exception as e:
            raise Exception(f"Failed to send message: {str(e)}")

    def close(self):
        self.running = False
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        finally:
            self.socket.close()

class MessengerServer:
    def __init__(self, host='localhost', port=5000):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.host = host
        self.port = port
        self.clients = []
        self.clients_lock = threading.Lock()
        self.running = True
        self.BUFFER_SIZE = 4096

    def start(self):
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            logging.info(f"Server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    ready = select.select([self.socket], [], [], 0.1)
                    if ready[0]:
                        client, address = self.socket.accept()
                        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        logging.info(f"New connection from {address}")
                        with self.clients_lock:
                            self.clients.append(client)
                        thread = threading.Thread(target=self.handle_client, args=(client,))
                        thread.daemon = True
                        thread.start()
                except Exception as e:
                    if self.running:
                        logging.error(f"Error accepting client connection: {e}")
        except Exception as e:
            logging.error(f"Server error: {str(e)}")
        finally:
            self.close()

    def _receive_data(self, client):
        try:
            length_data = client.recv(4)
            if not length_data or len(length_data) != 4:
                return None
            
            length = int.from_bytes(length_data, byteorder='big')
            if length > 1048576:  # Limit message size to 1MB
                raise ValueError("Message too large")
            
            chunks = []
            bytes_received = 0
            while bytes_received < length:
                chunk = client.recv(min(length - bytes_received, self.BUFFER_SIZE))
                if not chunk:
                    return None
                chunks.append(chunk)
                bytes_received += len(chunk)
            
            compressed_data = b''.join(chunks)
            json_data = zlib.decompress(compressed_data).decode('utf-8')
            return json.loads(json_data)
        except Exception as e:
            logging.error(f"Receive error: {str(e)}")
            return None

    def _send_data(self, client, data):
        try:
            json_data = json.dumps(data)
            compressed = zlib.compress(json_data.encode('utf-8'))
            
            length = len(compressed)
            client.sendall(length.to_bytes(4, byteorder='big'))
            client.sendall(compressed)
            return True
        except Exception as e:
            logging.error(f"Send error: {str(e)}")
            return False

    def handle_client(self, client):
        while self.running:
            try:
                data = self._receive_data(client)
                if not data:
                    break
                self.broadcast(data, client)
            except Exception as e:
                logging.error(f"Client handler error: {str(e)}")
                break
        self.remove_client(client)

    def broadcast(self, data, sender_socket):
        message = f"[{data['timestamp']}] {data['username']}: {data['message']}"
        broadcast_data = {
            'message': message,
            'type': 'broadcast'
        }
        
        with self.clients_lock:
            disconnected_clients = []
            for client in self.clients:
                if client != sender_socket:
                    if not self._send_data(client, broadcast_data):
                        disconnected_clients.append(client)
            
            for client in disconnected_clients:
                self.remove_client(client)

    def remove_client(self, client):
        with self.clients_lock:
            if client in self.clients:
                self.clients.remove(client)
                try:
                    client.close()
                except Exception as e:
                    logging.error(f"Error closing client connection: {str(e)}")
                logging.info(f"Client disconnected. Active clients: {len(self.clients)}")

    def close(self):
        self.running = False
        with self.clients_lock:
            for client in self.clients[:]:
                self.remove_client(client)
        try:
            self.socket.close()
        except Exception as e:
            logging.error(f"Error closing server socket: {str(e)}")