"""Lightweight Flask HTTP API for scenario control.

Runs on port 5001 inside the modbus_sim container.
Called by the NEXUS API demo router to trigger named demo scenarios.

Endpoints:
    GET  /scenario          → current scenario status
    POST /scenario          → body: {"scenario": "LINE_FAULT"}
    GET  /health            → liveness probe
"""

from __future__ import annotations

import json
import logging

from flask import Flask, Response, request
from scenario_state import set_scenario, status

LOG = logging.getLogger("scenario_api")
app = Flask(__name__)


@app.get("/health")
def health() -> Response:
    return Response(json.dumps({"ok": True}), mimetype="application/json")


@app.get("/scenario")
def get_scenario_route() -> Response:
    return Response(json.dumps(status()), mimetype="application/json")


@app.post("/scenario")
def set_scenario_route() -> Response:
    body = request.get_json(silent=True) or {}
    name = body.get("scenario", "")
    try:
        set_scenario(name)
        LOG.info("scenario changed to %s", name)
        return Response(json.dumps(status()), mimetype="application/json", status=200)
    except ValueError as exc:
        return Response(json.dumps({"error": str(exc)}), mimetype="application/json", status=422)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5001, threaded=True)


if __name__ == "__main__":
    run()
