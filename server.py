from analytics_mcp.fastmcp_app import mcp
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

app = mcp.http_app(stateless_http=True)


def helathz(_request: Request) -> Response:
    return JSONResponse(content={"status": "ok"}, status_code=200)


app.add_route("/healthz", helathz, methods=["GET"])
