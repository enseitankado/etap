import socket
import os
import pwd
import json
import threading
import sys
import time
import traceback

class UnixSocketService:
    def __init__(self, path):
        self.server = None
        self.SOCKET_PATH = path
        self.running = True
        self.event = None

        self.cleanup_socket()

    def cleanup_socket(self):
        """ Clean up socket file if exists """
        try:
            if os.path.exists(self.SOCKET_PATH):
                os.remove(self.SOCKET_PATH)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"(unix_socket) Socket cleanup error: {e}", file=sys.stderr)

    def handle_client(self, connection):
        """ Handle client requests """
        try:
            data = connection.recv(1024).decode()
            request = json.loads(data)
            if self.event:
                self.event(request)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"(unix_socket) Client handling error: {e}", file=sys.stderr)
        finally:
            connection.close()

    def run(self):

        self.cleanup_socket()

        try:
            self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server.bind(self.SOCKET_PATH)
            self.server.listen(5)

            lightdm_info = pwd.getpwnam("lightdm")
            lightdm_uid = lightdm_info.pw_uid
            os.chmod(self.SOCKET_PATH, 0o700)
            os.chown(self.SOCKET_PATH, lightdm_uid, -1)

            print(f"(unix_socket) Running at {self.SOCKET_PATH}", file=sys.stderr)

            while self.running:
                conn, _ = self.server.accept()
                print(f"(unix_socket) New Connection: {conn}", file=sys.stderr)
                threading.Thread(target=self.handle_client, args=(conn,)).start()

        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"(unix_socket) Server error: {e}", file=sys.stderr)

        finally:
            self.cleanup_socket()
            if self.server:
                self.server.close()

if __name__ == "__main__":
    service = UnixSocketService()
    service.run()
