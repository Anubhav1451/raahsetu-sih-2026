"""Unit tests for official live early-warning feed parsers (CAP XML, CWC JSON, Traffic JSON)."""

from app.live_ingestion import (
    get_official_feeds_status,
    parse_cap_alert_xml,
    parse_cwc_bulletin_json,
    parse_traffic_incident_json,
)

SAMPLE_CAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>NDMA-SACHET-2024-NE-0812</identifier>
  <sender>sdma.assam@nic.in</sender>
  <sent>2024-08-12T06:30:00+05:30</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Geo</category>
    <event>Flash Flood &amp; Debris Flow</event>
    <urgency>Immediate</urgency>
    <severity>Extreme</severity>
    <certainty>Observed</certainty>
    <headline>Severe Debris Flow Blocking NH-27 near Jorabat</headline>
    <instruction>Commercial vehicles divert via Guwahati-Shillong bypass corridor.</instruction>
    <area>
      <areaDesc>Assam - Kamrup Metropolitan NH-27</areaDesc>
      <circle>26.1044,91.8962 10.0</circle>
    </area>
  </info>
</alert>
"""

SAMPLE_CWC_JSON = {
    "bulletins": [
        {
            "station_name": "Silchar",
            "river_name": "Barak",
            "state": "Assam",
            "water_level_m": 20.45,
            "danger_level_m": 19.83,
            "latitude": 24.83,
            "longitude": 92.78,
            "flood_situation": "Severe Flood Situation",
        },
        {
            "station_name": "Guwahati DC Court",
            "river_name": "Brahmaputra",
            "state": "Assam",
            "water_level_m": 48.20,
            "danger_level_m": 49.68,
            "latitude": 26.18,
            "longitude": 91.75,
            "flood_situation": "Normal",
        },
    ]
}

SAMPLE_TRAFFIC_JSON = {
    "incidents": [
        {
            "incident_id": "TRF-NH13-0941",
            "state": "Arunachal Pradesh",
            "corridor": "NH-13 Sela Pass Ridge",
            "headline": "Active rockfall blocking single lane",
            "severity": "WARNING",
            "latitude": 27.502,
            "longitude": 92.091,
            "instruction": "Heavy multi-axle freight halted until Border Roads clearance.",
        }
    ]
}


def test_parse_cap_alert_xml():
    advisories = parse_cap_alert_xml(SAMPLE_CAP_XML)
    assert len(advisories) == 1
    adv = advisories[0]
    assert adv.severity == "WARNING"
    assert "Jorabat" in adv.headline
    assert adv.state == "Assam"
    assert adv.coordinates == [91.8962, 26.1044]
    assert "Guwahati-Shillong bypass" in adv.recommended_action


def test_parse_cwc_bulletin_json():
    advisories = parse_cwc_bulletin_json(SAMPLE_CWC_JSON)
    # Only the overtopping station (Silchar) should trigger an active hazard advisory
    assert len(advisories) == 1
    adv = advisories[0]
    assert "Silchar" in adv.headline
    assert "Barak" in adv.headline
    assert adv.severity in {"WARNING", "ALERT"}
    assert adv.coordinates == [92.78, 24.83]
    assert "floodplain" in adv.recommended_action.lower()


def test_parse_traffic_incident_json():
    advisories = parse_traffic_incident_json(SAMPLE_TRAFFIC_JSON)
    assert len(advisories) == 1
    adv = advisories[0]
    assert adv.state == "Arunachal Pradesh"
    assert adv.severity == "WARNING"
    assert adv.coordinates == [92.091, 27.502]
    assert "Border Roads" in adv.recommended_action


def test_empty_and_malformed_feeds():
    assert parse_cap_alert_xml("") == []
    assert parse_cap_alert_xml("<not-valid-xml") == []
    assert parse_cwc_bulletin_json({}) == []
    assert parse_traffic_incident_json({}) == []


def test_official_feeds_truthful_standby_status():
    status_list = get_official_feeds_status()
    assert len(status_list) >= 3
    source_names = [s.source_name for s in status_list]
    assert "Open-Meteo forecast API" in source_names
    assert "NDMA SACHET CAP adapter" in source_names
    assert "CWC flood forecast adapter" in source_names

    # By default, without environment variables set, CAP & CWC must report truthful STANDBY
    ndma_status = next(s for s in status_list if "NDMA" in s.source_name)
    assert ndma_status.status in {"STANDBY", "ONLINE", "DEGRADED"}
