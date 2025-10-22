from __future__ import annotations

import os
from typing import Any, Dict

from flask import Flask, jsonify, render_template

from .data_service import PumpFunDataService


DEFAULT_REFRESH_INTERVAL = int(os.getenv("PUMP_FUN_REFRESH_SECONDS", "30"))


def create_app(data_source: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    data_service = PumpFunDataService(data_source=data_source)

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html",
            auto_refresh_seconds=DEFAULT_REFRESH_INTERVAL,
        )

    @app.route("/api/data")
    def get_data() -> Dict[str, Any]:
        dataset = data_service.load()
        return jsonify(dataset)

    @app.route("/healthz")
    def healthcheck() -> Dict[str, str]:
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
