import http.server
import socketserver
import os

STATIC_DIR = "/app/static"
PORT = 8080


class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        # ពិនិត្យមើលថាតើ File ដែលស្នើសុំមានឬទេ
        path = self.translate_path(self.path)

        # បើ File មិនមាន ឬជាថត សូមបញ្ជូនទៅ index.html (សម្រាប់ React Router)
        if not os.path.exists(path) or os.path.isdir(path):
            self.path = "/index.html"

        return super().do_GET()

    def log_message(self, format, *args):
        # បង្ហាញ Log សាមញ្ញ
        print(f"{self.address_string()} - {format % args}")


with socketserver.TCPServer(("0.0.0.0", PORT), SPAHandler) as httpd:
    print(f"🚀 Serving KlearStudy Frontend on port {PORT}")
    httpd.serve_forever()