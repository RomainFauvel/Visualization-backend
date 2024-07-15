import psutil
import socket
import threading
import sys
import pandas as pd

def get_raspberry_pi_ip():
    try:
        # Connect to an external server to get the local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('8.8.8.8', 1))  # Use Google Public DNS server address
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Error getting IP address: {e}")
        return None

def get_used_local_ports():
    raspberry_pi_ip = get_raspberry_pi_ip()
    if not raspberry_pi_ip:
        return set()
    
    used_ports = set()
    connections = psutil.net_connections(kind='inet')
    
    for conn in connections:
        if conn.laddr and conn.laddr.ip == raspberry_pi_ip:  # Check for Raspberry Pi IP
            used_ports.add(conn.laddr.port)
    
    return used_ports

def find_first_available_local_port(start_port=49152, end_port=65535):
    used_ports = get_used_local_ports()
    
    for port in range(start_port, end_port + 1):
        if port not in used_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((get_raspberry_pi_ip(), port))
                    return port
                except OSError:
                    continue
    return None  # Return None if no available port is found

class ControlledThread(threading.Thread):
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run      
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
        if event == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg):
        if self.killed:
            if event == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True

class CustomDataFrame(pd.DataFrame):
    _metadata = ['path']
    
    def __init__(self, *args, path=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = path
    
    @property
    def _constructor(self):
        return CustomDataFrame

if __name__ == "__main__":
    # Example usage
    available_port = find_first_available_local_port()
    if available_port:
        print(f"First available local port: {available_port}")
    else:
        print("No available local port found")
