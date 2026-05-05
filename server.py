from analytics_mcp.fastmcp import mcp
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

app = mcp.http_app()

def helathz(_request: Request) -> Response:
    return JSONResponse(content={"status": "ok"}, status_code=200)

app.add_route("/healthz", helathz, methods=["GET"])
