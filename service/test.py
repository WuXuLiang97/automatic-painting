import socket
import json
import struct
import cv2
import numpy as np

def connect_server(server_ip, server_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port))
    return sock

def send_request(sock, req_type, image):
    img_bytes = cv2.imencode('.jpg', image)[1].tobytes()
    image_size = len(img_bytes)
    header_data = json.dumps({"type": req_type, "image_size": image_size}).encode('utf-8')
    header_length = struct.pack('!I', len(header_data))
    sock.sendall(header_length)
    sock.sendall(header_data)
    sock.sendall(img_bytes)
    return sock

def receive_response(sock):
    header_len = sock.recv(4)
    if len(header_len) < 4:
        return None
    header_size = struct.unpack("!I", header_len)[0]
    header_data = sock.recv(header_size)
    header = json.loads(header_data.decode('utf-8'))
    data_size = header['data_size']
    data = sock.recv(data_size)
    result = json.loads(data.decode('utf-8'))
    return result

if __name__ == "__main__":
    sock = connect_server("192.168.0.34", 12345)
    send_request(sock, "game_windows", np.zeros((640, 640, 3), dtype=np.uint8))
    result = receive_response(sock)
    print(result)
    sock.close()