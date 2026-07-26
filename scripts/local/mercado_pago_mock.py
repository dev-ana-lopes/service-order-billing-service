from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MercadoPagoMockHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"detail": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/checkout/preferences":
            self._send_json(404, {"detail": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length) or b"{}")
        external_reference = str(payload.get("external_reference", "local-demo"))
        quote_item = payload.get("items", [{}])[0]
        preference_id = str(quote_item.get("id", "pref-local-demo"))
        self._send_json(
            201,
            {
                "id": f"pref-{preference_id}",
                "init_point": f"http://localhost:8002/mock-checkout/{external_reference}",
                "sandbox_init_point": f"http://localhost:8002/mock-checkout/{external_reference}",
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        return None

    def _send_json(self, status_code: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", 8080), MercadoPagoMockHandler)
    print("[mercado-pago-mock] Listening on 0.0.0.0:8080", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
