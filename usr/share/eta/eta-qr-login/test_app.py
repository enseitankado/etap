#!/usr/bin/env python3
# Test qr reader for binary eye android application
# https://f-droid.org/packages/de.markusfisch.android.binaryeye/

# Usage: test_app.py <user-token>
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import time
import sys

hostName = "0.0.0.0"
serverPort = 8000

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        uuid=self.path.split("?")[-1].split("=")[-1]
        j = {"token":str(sys.argv[1])}
        print(j)
        requests.post("https://qr-etap.eba.gov.tr/api/v1/eba-callback/"+uuid, json=j)
        self.end_headers()

webServer = HTTPServer((hostName, serverPort), MyServer)
print("Server started http://%s:%s" % (hostName, serverPort))

webServer.serve_forever()

webServer.server_close()
print("Server stopped.")

