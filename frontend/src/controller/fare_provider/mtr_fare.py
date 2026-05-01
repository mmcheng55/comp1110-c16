import csv
import io
import requests
from .base_fare import BaseFareProvider
from utils import normalize_stop_name

MTR_FARE_CSV_URL = "https://opendata.mtr.com.hk/data/mtr_lines_fares.csv" # A hypothetical or real endpoint

class MtrFareProvider(BaseFareProvider):
    def fetch_fares(self) -> dict:
        try:
            response = requests.get(MTR_FARE_CSV_URL, timeout=20)
            response.encoding = 'utf-8-sig'
            response.raise_for_status()
            return self._parse_csv(response.text)
        except Exception as e:
            print(f"Failed to fetch MTR fares: {e}")
            return {}

    def _parse_csv(self, csv_text: str) -> dict:
        fares = {}
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            return fares
            
        src_keys = ["SRC_STATION_NAME", "Src station", "Source", "From"]
        dest_keys = ["DEST_STATION_NAME", "Dest station", "Destination", "To"]
        fare_keys = ["OCT_ADT_FARE", "Adult Octopus", "Fare", "Cost"]
        
        src_key = next((k for k in src_keys if k in reader.fieldnames), reader.fieldnames[0])
        dest_key = next((k for k in dest_keys if k in reader.fieldnames), reader.fieldnames[1] if len(reader.fieldnames) > 1 else None)
        fare_key = next((k for k in fare_keys if k in reader.fieldnames), reader.fieldnames[2] if len(reader.fieldnames) > 2 else None)
        
        if not dest_key or not fare_key:
            return fares
            
        for row in reader:
            src = normalize_stop_name(row.get(src_key, ""))
            dest = normalize_stop_name(row.get(dest_key, ""))
            try:
                fare = float(row.get(fare_key, 0))
            except ValueError:
                continue
                
            if src and dest:
                fares[(src, dest)] = fare
                fares[(dest, src)] = fare
                
        return fares
