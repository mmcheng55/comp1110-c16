import pytest
from controller.route_provider.mtr_crawler import MtrDataProvider
def test_parse_mtr_network_csv():
    csv_data = """line_code,direction,english_name,sequence
TWL,UP,Central,1
TWL,UP,Admiralty,2
TWL,UP,Tsim Sha Tsui,3
"""
    crawler = MtrDataProvider()
    network = crawler._parse_mtr_network_csv(csv_data)
    # 3 unique stops
    assert len(network["stops"]) == 3
    # 2 edges (Central-Admiralty, Admiralty-TST), undirected means 4 directed segments
    assert len(network["segments"]) == 4 
    stops = {s["stopName"] for s in network["stops"]}
    assert stops == {"Central", "Admiralty", "Tsim Sha Tsui"}
    # Verify Central -> Admiralty edge exists with correct line
    found_seg = next((seg for seg in network["segments"] if seg["from"]["stopName"] == "Central" and seg["to"]["stopName"] == "Admiralty"), None)
    assert found_seg is not None
    assert found_seg["line"] == "TWL"
def test_empty_csv_raises_error():
    crawler = MtrDataProvider()
    with pytest.raises(ValueError, match="MTR CSV is empty"):
        crawler._parse_mtr_network_csv("")
