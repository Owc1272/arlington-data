"""
Quick local server for the Arlington Data Explorer.
Run: python serve.py
Then open http://localhost:8080 in your browser.
"""
import http.server
import socketserver
import webbrowser
import os

PORT = 8080
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

Handler = http.server.SimpleHTTPRequestHandler
with ThreadedHTTPServer(("", PORT), Handler) as httpd:
    url = f"http://localhost:{PORT}"
    print(f"Serving Arlington Data Explorer at {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)
    httpd.serve_forever()
