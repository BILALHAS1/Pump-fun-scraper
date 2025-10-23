from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Generator

from flask import Flask, Response, jsonify, render_template

from .data_service import PumpFunDataService


DEFAULT_REFRESH_INTERVAL = max(1, int(os.getenv("PUMP_FUN_REFRESH_SECONDS", "20")))
LIVE_UPDATE_INTERVAL = max(
    1,
    int(os.getenv("PUMP_FUN_LIVE_INTERVAL", str(DEFAULT_REFRESH_INTERVAL))),
)

logger = logging.getLogger(__name__)

def create_app(data_source: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    data_service = PumpFunDataService(data_source=data_source)
    logger.info("Dashboard using data source: %s", data_service.data_source)

    # Track known coins to detect new ones
    known_coin_ids = set()

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html",
            auto_refresh_seconds=DEFAULT_REFRESH_INTERVAL,
            live_mode=True,
        )

    @app.route("/api/data")
    def get_data() -> Dict[str, Any]:
        dataset = data_service.load()
        tokens = dataset.get("tokens", [])
        logger.info(
            "API response: %d tokens (source=%s, sample=%s)",
            len(tokens),
            dataset.get("source_path"),
            dataset.get("using_sample_data"),
        )
        return jsonify(dataset)

    @app.route("/api/stream")
    def stream() -> Response:
        """Server-Sent Events endpoint for real-time updates"""
        
        def generate() -> Generator[str, None, None]:
            nonlocal known_coin_ids
            
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Live updates active'})}\n\n"
            
            while True:
                try:
                    dataset = data_service.load()
                    tokens = dataset.get("tokens", [])
                    dataset_source = dataset.get("source_path")
                    using_sample = dataset.get("using_sample_data")
                    logger.info(
                        "Stream update loaded %d tokens (source=%s, sample=%s)",
                        len(tokens),
                        dataset_source,
                        using_sample,
                    )

                    # Detect new coins
                    new_coins = []
                    current_coin_ids = set()
                    
                    for token in tokens:
                        coin_id = token.get("mint_address") or token.get("symbol") or token.get("name")
                        if coin_id:
                            current_coin_ids.add(coin_id)
                            if coin_id not in known_coin_ids:
                                new_coins.append(token)

                    if new_coins:
                        coin_labels = [
                            token.get("symbol")
                            or token.get("name")
                            or token.get("mint_address")
                            for token in new_coins[:5]
                        ]
                        display_labels = ", ".join(filter(None, coin_labels))
                        if len(new_coins) > 5:
                            display_labels = f"{display_labels}, ..." if display_labels else "..."
                        logger.info(
                            "Stream detected %d new coins: %s",
                            len(new_coins),
                            display_labels or "unidentified coins",
                        )
                    
                    # Update known coins
                    known_coin_ids = current_coin_ids
                    
                    # Prepare update data
                    update_data = {
                        "type": "update",
                        "timestamp": time.time(),
                        "tokens": tokens,
                        "new_coins": new_coins,
                        "dataset_timestamp": dataset.get("dataset_timestamp"),
                        "using_sample_data": dataset.get("using_sample_data", False),
                    }
                    
                    yield f"data: {json.dumps(update_data)}\n\n"
                    
                    time.sleep(LIVE_UPDATE_INTERVAL)
                    
                except Exception as e:
                    logger.exception("Error streaming dashboard data")
                    error_data = {
                        "type": "error",
                        "message": str(e),
                        "timestamp": time.time(),
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    time.sleep(LIVE_UPDATE_INTERVAL)
        
        return Response(generate(), mimetype="text/event-stream")

    @app.route("/healthz")
    def healthcheck() -> Dict[str, str]:
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
