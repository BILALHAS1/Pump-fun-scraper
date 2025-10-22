from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from dateutil import parser

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE_FILE = BASE_DIR / "sample_output.json"


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parser.isoparse(value)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0



def _normalise_collection(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return list(data)
    if isinstance(data, dict):
        for key in (
            "data",
            "tokens",
            "transactions",
            "new_launches",
            "items",
            "rows",
            "records",
        ):
            value = data.get(key)
            if isinstance(value, list):
                return list(value)
        if all(isinstance(value, dict) for value in data.values()):
            return list(data.values())
    return []


@dataclass
class LoadedData:
    tokens: List[Dict[str, Any]]
    transactions: List[Dict[str, Any]]
    new_launches: List[Dict[str, Any]]
    scrape_metadata: Dict[str, Any]
    statistics: Dict[str, Any]
    source_path: Path
    using_sample_data: bool
    dataset_timestamp: Optional[datetime]


class PumpFunDataService:
    """Loads and enriches Pump.fun scrape datasets from JSON/CSV outputs."""

    def __init__(self, data_source: Optional[str] = None) -> None:
        source = data_source or os.getenv("PUMP_FUN_DATA_SOURCE") or os.getenv(
            "PUMP_FUN_DATA_FILE"
        )
        if source:
            self.data_source = Path(source).expanduser().resolve()
        else:
            self.data_source = DEFAULT_SAMPLE_FILE

    def load(self) -> Dict[str, Any]:
        raw = self._load_raw_data()
        summary = self._build_summary(raw.tokens, raw.transactions, raw.statistics)
        charts = self._build_charts(raw.tokens, raw.transactions, raw.new_launches)
        launches_timeline = self._build_launches_timeline(raw.new_launches)

        generated_at = datetime.now(timezone.utc)
        dataset_timestamp = raw.dataset_timestamp or summary.get("latest_activity")
        dataset_timestamp_iso = (
            dataset_timestamp.isoformat().replace("+00:00", "Z")
            if isinstance(dataset_timestamp, datetime)
            else None
        )

        scrape_timestamp = raw.scrape_metadata.get("timestamp")
        return {
            "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
            "dataset_timestamp": dataset_timestamp_iso,
            "scrape_metadata": raw.scrape_metadata,
            "statistics": raw.statistics,
            "tokens": raw.tokens,
            "transactions": raw.transactions,
            "new_launches": raw.new_launches,
            "summary": summary,
            "charts": charts,
            "launches_timeline": launches_timeline,
            "source_path": str(raw.source_path),
            "using_sample_data": raw.using_sample_data,
            "scrape_timestamp": scrape_timestamp,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_raw_data(self) -> LoadedData:
        source = self.data_source
        using_sample = False
        dataset_timestamp: Optional[datetime] = None

        if source.is_file():
            data = self._read_json(source)
            dataset_timestamp = _parse_iso_timestamp(
                data.get("scrape_metadata", {}).get("timestamp")
            )
            return LoadedData(
                tokens=list(data.get("tokens", [])),
                transactions=list(data.get("transactions", [])),
                new_launches=list(data.get("new_launches", [])),
                scrape_metadata=dict(data.get("scrape_metadata", {})),
                statistics=dict(data.get("statistics", {})),
                source_path=source,
                using_sample_data=source.samefile(DEFAULT_SAMPLE_FILE),
                dataset_timestamp=dataset_timestamp,
            )

        if source.is_dir():
            tokens, tokens_timestamp = self._load_latest_collection(
                source / "tokens", prefix="tokens_"
            )
            if not tokens:
                tokens, tokens_timestamp = self._load_latest_collection(
                    source, prefix="tokens_"
                )

            transactions, transactions_timestamp = self._load_latest_collection(
                source / "transactions", prefix="transactions_"
            )
            if not transactions:
                transactions, transactions_timestamp = self._load_latest_collection(
                    source, prefix="transactions_"
                )

            new_launches, launches_timestamp = self._load_latest_collection(
                source / "launches", prefix="new_launches_"
            )
            if not new_launches:
                new_launches, launches_timestamp = self._load_latest_collection(
                    source, prefix="new_launches_"
                )
            if not new_launches:
                new_launches, launches_timestamp = self._load_latest_collection(
                    source, prefix="launches_"
                )

            scrape_metadata, metadata_timestamp = self._load_session_metadata(source)
            statistics = self._load_statistics(source)

            dataset_timestamp = max(
                [
                    ts
                    for ts in [
                        tokens_timestamp,
                        transactions_timestamp,
                        launches_timestamp,
                        metadata_timestamp,
                    ]
                    if ts is not None
                ],
                default=None,
            )

            return LoadedData(
                tokens=tokens,
                transactions=transactions,
                new_launches=new_launches,
                scrape_metadata=scrape_metadata,
                statistics=statistics,
                source_path=source,
                using_sample_data=False,
                dataset_timestamp=dataset_timestamp,
            )

        # Fallback to included sample data
        using_sample = True
        data = self._read_json(DEFAULT_SAMPLE_FILE)
        dataset_timestamp = _parse_iso_timestamp(
            data.get("scrape_metadata", {}).get("timestamp")
        )
        return LoadedData(
            tokens=list(data.get("tokens", [])),
            transactions=list(data.get("transactions", [])),
            new_launches=list(data.get("new_launches", [])),
            scrape_metadata=dict(data.get("scrape_metadata", {})),
            statistics=dict(data.get("statistics", {})),
            source_path=DEFAULT_SAMPLE_FILE,
            using_sample_data=using_sample,
            dataset_timestamp=dataset_timestamp,
        )

    def _load_latest_collection(
        self, directory: Path, prefix: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[datetime]]:
        if not directory.exists() or not directory.is_dir():
            return [], None
        data_file = self._find_latest_json(directory, prefix=prefix)
        loader = self._read_json

        if not data_file:
            data_file = self._find_latest_csv(directory, prefix=prefix)
            loader = self._read_csv

        if not data_file:
            return [], None

        data = loader(data_file)
        items = [item for item in _normalise_collection(data) if isinstance(item, dict)]
        timestamp = self._guess_timestamp_from_filename(data_file.name)

        if not timestamp and isinstance(data, dict):
            for key in ("timestamp", "scraped_at", "generated_at", "created_at"):
                ts_value = data.get(key)
                ts_parsed = _parse_iso_timestamp(ts_value)
                if ts_parsed:
                    timestamp = ts_parsed
                    break

        if not timestamp:
            timestamp = datetime.fromtimestamp(
                data_file.stat().st_mtime, tz=timezone.utc
            )

        return items, timestamp

    def _load_session_metadata(
        self, directory: Path
    ) -> Tuple[Dict[str, Any], Optional[datetime]]:
        session_files = sorted(directory.glob("session_stats*.json"))
        if not session_files:
            return {}, None
        latest = max(session_files, key=lambda path: path.stat().st_mtime)
        data = self._read_json(latest)
        timestamp = self._guess_timestamp_from_filename(latest.name)

        timestamp_candidate = (
            data.get("timestamp")
            or data.get("generated_at")
            or data.get("scrape_timestamp")
            or data.get("scraped_at")
        )

        parsed_timestamp = _parse_iso_timestamp(timestamp_candidate)
        if parsed_timestamp:
            timestamp = parsed_timestamp

        if not timestamp:
            timestamp = datetime.fromtimestamp(
                latest.stat().st_mtime, tz=timezone.utc
            )

        metadata = {
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "total_tokens": data.get("total_tokens")
            or data.get("token_count"),
            "total_transactions": data.get("total_transactions"),
            "total_new_launches": data.get("total_new_launches"),
            "session_duration_seconds": data.get("session_duration_seconds"),
        }
        return metadata, timestamp

    def _load_statistics(self, directory: Path) -> Dict[str, Any]:
        stats_file = directory / "session_stats.json"
        if stats_file.exists():
            return self._read_json(stats_file)
        # otherwise look for aggregated stats in metadata load
        session_files = sorted(directory.glob("session_stats*.json"))
        if session_files:
            latest = max(session_files, key=lambda path: path.stat().st_mtime)
            return self._read_json(latest)
        return {}

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def _read_csv(path: Path) -> List[Dict[str, Any]]:
        with path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            return [dict(row) for row in reader]

    @staticmethod
    def _find_latest_json(directory: Path, prefix: Optional[str] = None) -> Optional[Path]:
        if prefix:
            json_files = list(directory.glob(f"{prefix}*.json"))
        else:
            json_files = list(directory.glob("*.json"))
        if not json_files:
            return None
        return max(json_files, key=lambda path: path.stat().st_mtime)

    @staticmethod
    def _find_latest_csv(directory: Path, prefix: Optional[str] = None) -> Optional[Path]:
        if prefix:
            csv_files = list(directory.glob(f"{prefix}*.csv"))
        else:
            csv_files = list(directory.glob("*.csv"))
        if not csv_files:
            return None
        return max(csv_files, key=lambda path: path.stat().st_mtime)

    @staticmethod
    def _guess_timestamp_from_filename(filename: str) -> Optional[datetime]:
        parts = filename.split("_")
        if len(parts) < 2:
            return None
        candidate = parts[-1].split(".")[0]
        try:
            dt = datetime.strptime(candidate, "%Y%m%d%H%M%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                dt = datetime.strptime(candidate, "%Y%m%d%H%M%S%f")
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return None

    # ------------------------------------------------------------------
    # Summary + chart data builders
    # ------------------------------------------------------------------
    def _build_summary(
        self,
        tokens: Iterable[Dict[str, Any]],
        transactions: Iterable[Dict[str, Any]],
        statistics: Dict[str, Any],
    ) -> Dict[str, Any]:
        tokens_list = list(tokens)
        transactions_list = list(transactions)

        total_tokens = len(tokens_list)
        total_transactions = len(transactions_list)
        total_market_cap = sum(_safe_float(t.get("market_cap")) for t in tokens_list)
        total_volume_24h = sum(_safe_float(t.get("volume_24h")) for t in tokens_list)

        buy_volume = 0.0
        sell_volume = 0.0
        for tx in transactions_list:
            action = str(tx.get("action", "")).lower()
            amount = _safe_float(tx.get("amount"))
            price = _safe_float(tx.get("price"))
            value = amount * price if price else amount
            if action == "buy":
                buy_volume += value
            elif action == "sell":
                sell_volume += value

        latest_activity_candidates = []
        for token in tokens_list:
            ts = _parse_iso_timestamp(token.get("scraped_at") or token.get("created_timestamp"))
            if ts:
                latest_activity_candidates.append(ts)
        for tx in transactions_list:
            ts = _parse_iso_timestamp(tx.get("timestamp") or tx.get("scraped_at"))
            if ts:
                latest_activity_candidates.append(ts)

        latest_activity = max(latest_activity_candidates) if latest_activity_candidates else None

        top_token = None
        if tokens_list:
            top_token = max(
                tokens_list,
                key=lambda token: _safe_float(token.get("market_cap")),
            )

        summary = {
            "total_tokens": total_tokens,
            "total_transactions": total_transactions,
            "total_market_cap": total_market_cap,
            "total_volume_24h": total_volume_24h,
            "buy_volume_value": buy_volume,
            "sell_volume_value": sell_volume,
            "latest_activity": latest_activity.isoformat().replace("+00:00", "Z")
            if latest_activity
            else None,
            "top_token": {
                "name": top_token.get("name") if top_token else None,
                "symbol": top_token.get("symbol") if top_token else None,
                "market_cap": _safe_float(top_token.get("market_cap")) if top_token else None,
                "price": _safe_float(top_token.get("price")) if top_token else None,
            }
            if top_token
            else None,
            "stats_provided": bool(statistics),
        }

        if statistics:
            summary["success_rate"] = statistics.get("session_stats", {}).get(
                "success_rate_percent"
            )
            summary["avg_response_time_ms"] = statistics.get("session_stats", {}).get(
                "average_response_time_ms"
            )
            summary["unique_users"] = statistics.get("transaction_stats", {}).get(
                "unique_users"
            )

        return summary

    def _build_charts(
        self,
        tokens: Iterable[Dict[str, Any]],
        transactions: Iterable[Dict[str, Any]],
        new_launches: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        tokens_list = list(tokens)
        transactions_list = list(transactions)
        launches_list = list(new_launches)

        # Price trend chart - tokens sorted by creation timestamp
        sortable_tokens = [
            (
                _parse_iso_timestamp(token.get("created_timestamp"))
                or _parse_iso_timestamp(token.get("scraped_at"))
                or datetime.min.replace(tzinfo=timezone.utc),
                token,
            )
            for token in tokens_list
        ]
        sortable_tokens.sort(key=lambda item: item[0])

        price_trend_labels = [token.get("symbol") or token.get("name") or "?" for _, token in sortable_tokens]
        price_trend_prices = [_safe_float(token.get("price")) for _, token in sortable_tokens]
        price_trend_market_caps = [_safe_float(token.get("market_cap")) for _, token in sortable_tokens]

        # Volume by token chart from transactions
        volume_by_token: Dict[str, Dict[str, float]] = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
        token_name_lookup = {
            token.get("mint_address") or token.get("symbol") or token.get("name"): token
            for token in tokens_list
        }
        for tx in transactions_list:
            mint = tx.get("token_mint") or tx.get("mint_address")
            action = str(tx.get("action", "")).lower()
            amount = _safe_float(tx.get("amount"))
            price = _safe_float(tx.get("price"))
            value = amount * price if price else amount
            identifier = mint or tx.get("symbol") or tx.get("name")
            if not identifier:
                continue
            entry = volume_by_token[identifier]
            if action == "buy":
                entry["buy"] += value
            elif action == "sell":
                entry["sell"] += value

        volume_labels = []
        volume_buy_values = []
        volume_sell_values = []
        for identifier, values in volume_by_token.items():
            token = token_name_lookup.get(identifier)
            label = None
            if token:
                label = token.get("symbol") or token.get("name")
            if not label:
                label = identifier[:6]
            volume_labels.append(label)
            volume_buy_values.append(round(values["buy"], 2))
            volume_sell_values.append(round(values["sell"], 2))

        # Transactions timeline (per hour)
        timeline_counter = Counter()
        for tx in transactions_list:
            ts = _parse_iso_timestamp(tx.get("timestamp") or tx.get("scraped_at"))
            if ts:
                key = ts.replace(minute=0, second=0, microsecond=0)
                timeline_counter[key] += 1
        timeline_points = sorted(timeline_counter.items(), key=lambda item: item[0])
        transactions_timeline_labels = [
            ts.isoformat().replace("+00:00", "Z") for ts, _ in timeline_points
        ]
        transactions_timeline_counts = [count for _, count in timeline_points]

        # Launches timeline counts per hour
        launches_counter = Counter()
        for launch in launches_list:
            ts = _parse_iso_timestamp(launch.get("created_timestamp") or launch.get("scraped_at"))
            if ts:
                key = ts.replace(minute=0, second=0, microsecond=0)
                launches_counter[key] += 1
        launches_points = sorted(launches_counter.items(), key=lambda item: item[0])
        launches_timeline_labels = [
            ts.isoformat().replace("+00:00", "Z") for ts, _ in launches_points
        ]
        launches_timeline_counts = [count for _, count in launches_points]

        return {
            "price_trend": {
                "labels": price_trend_labels,
                "prices": price_trend_prices,
                "market_caps": price_trend_market_caps,
            },
            "volume_by_token": {
                "labels": volume_labels,
                "buy": volume_buy_values,
                "sell": volume_sell_values,
            },
            "transactions_timeline": {
                "labels": transactions_timeline_labels,
                "counts": transactions_timeline_counts,
            },
            "launches_timeline": {
                "labels": launches_timeline_labels,
                "counts": launches_timeline_counts,
            },
        }

    def _build_launches_timeline(
        self, new_launches: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        launches = []
        for launch in new_launches:
            ts = _parse_iso_timestamp(launch.get("created_timestamp") or launch.get("scraped_at"))
            launches.append(
                {
                    "name": launch.get("name"),
                    "symbol": launch.get("symbol"),
                    "timestamp": ts.isoformat().replace("+00:00", "Z") if ts else None,
                    "price": _safe_float(launch.get("price")),
                    "market_cap": _safe_float(launch.get("market_cap")),
                    "volume_24h": _safe_float(launch.get("volume_24h")),
                    "mint_address": launch.get("mint_address"),
                    "website": launch.get("website"),
                    "twitter": launch.get("twitter"),
                    "telegram": launch.get("telegram"),
                }
            )

        launches.sort(
            key=lambda item: item.get("timestamp") or "",
            reverse=True,
        )
        return launches
