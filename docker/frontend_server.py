from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONTEND_DIR = Path("/app/frontend/dist")

class FrontendHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for serving the built frontend.
    
    """
    def __init__(self, *args, **kwargs):
        """Init.
        
        Args:
            *args: args value.
            **kwargs: kwargs value.
        
        Returns:
            None.
        """
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def end_headers(self) -> None:
        """End headers.
        
        Returns:
            End headers result.
        """
        if self.path == "/" or self.path.endswith(".html"):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        """Do get.
        
        Returns:
            Do get result.
        """
        requested_path = FRONTEND_DIR / self.path.lstrip("/")
        if self.path != "/" and not requested_path.exists() and "." not in Path(self.path).name:
            self.path = "/index.html"
        super().do_GET()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 5174), FrontendHandler).serve_forever()
