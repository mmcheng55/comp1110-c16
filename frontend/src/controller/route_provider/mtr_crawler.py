import csv
import io
import requests
from config import BACKEND_URL
from .base_crawler import BaseProvider

MTR_CSV_URL = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"


class MtrDataProvider(BaseProvider):
    def fetch_network(self) -> dict:
        response = requests.get(MTR_CSV_URL, timeout=20)
        response.encoding = 'utf-8-sig'
        response.raise_for_status()
        return self._parse_mtr_network_csv(response.text)

    @staticmethod
    def _stop_payload(stop_name: str) -> dict:
        return {
            "stopName": stop_name,
            "segmentTransportationType": {"x": 0.0, "y": 0.0},
        }

    @staticmethod
    def _normalize_csv_key(value: str | None) -> str:
        if value is None:
            return ""
        return value.strip().strip('"').casefold()

    @staticmethod
    def _resolve_csv_keys(fieldnames: list[str]) -> tuple[str, str, str, str]:
        normalized_to_raw = {
            MtrDataProvider._normalize_csv_key(fn): fn
            for fn in fieldnames if fn is not None
        }
        alias_options = {
            "line_code": ["line code", "linecode", "line_code", "line"],
            "direction": ["direction", "dir"],
            "english_name": ["english name", "englishname", "english_name", "station name", "station"],
            "sequence": ["sequence", "seq", "order"],
        }
        resolved: dict[str, str] = {}

        for key, aliases in alias_options.items():
            for alias in aliases:
                raw = normalized_to_raw.get(alias)
                if raw is not None:
                    resolved[key] = raw
                    break

        if len(resolved) == 4:
            return resolved["line_code"], resolved["direction"], resolved["english_name"], resolved["sequence"]

        if len(fieldnames) >= 7:
            return fieldnames[0], fieldnames[1], fieldnames[5], fieldnames[6]

        raise ValueError("MTR CSV schema is not supported")

    def _parse_mtr_network_csv(self, csv_text: str) -> dict:
        if not csv_text.strip():
            raise ValueError("MTR CSV is empty")

        reader = csv.DictReader(io.StringIO(csv_text))

        if not reader.fieldnames:
            raise ValueError("MTR CSV schema is not supported")
        lc_key, dir_key, name_key, seq_key = self._resolve_csv_keys(reader.fieldnames)
        stops_by_name: dict[str, dict] = {}
        line_sequences: dict[tuple[str, str], list[tuple[float, str]]] = {}

        for row in reader:
            station_name = (row.get(name_key) or "").strip()
            line_code = (row.get(lc_key) or "").strip()
            direction = (row.get(dir_key) or "").strip()
            sequence_raw = (row.get(seq_key) or "").strip()
            if not station_name or not line_code or not direction:
                continue
            try:
                sequence_value = float(sequence_raw)
            except ValueError:
                continue
            stops_by_name.setdefault(station_name, self._stop_payload(station_name))
            line_sequences.setdefault((line_code, direction), []).append((sequence_value, station_name))

        if not stops_by_name:
            raise ValueError("No station data parsed from MTR CSV")
        segments: list[dict] = []
        seen = set()

        for (line_code, _dir), entries in line_sequences.items():
            ordered = sorted(entries, key=lambda item: item[0])
            for current, nxt in zip(ordered, ordered[1:]):
                from_name = current[1]
                to_name = nxt[1]
                if from_name == to_name:
                    continue

                undirected_edge_key = (line_code, min(from_name, to_name), max(from_name, to_name))

                if undirected_edge_key in seen:
                    continue

                seen.add(undirected_edge_key)

                base_segment = {
                    "type": "Train",
                    "line": line_code,
                    "fare": 5.0,
                    "time": 2,
                    "scenic": 3,
                }
                segments.append({**base_segment, "from": stops_by_name[from_name], "to": stops_by_name[to_name]})
                segments.append({**base_segment, "from": stops_by_name[to_name], "to": stops_by_name[from_name]})

        if not segments:
            raise ValueError("No segment data parsed from MTR CSV")

        return {"stops": list(stops_by_name.values()), "segments": segments}
