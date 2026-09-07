import random
from concurrent.futures import ThreadPoolExecutor

import networkx as nx
import pytest
from pydantic import ValidationError

from app.main import load_graph
from app.models import Dataset, Edge, Endpoint, Node, RouteRequest
from app.routing import RoadGraph


@pytest.fixture
def graph(monkeypatch):
    monkeypatch.delenv("DATASET_PATH", raising=False)
    return load_graph()


def request(origin="n2_0", destination="n2_6", **kwargs):
    return RouteRequest(
        origin=Endpoint(node_id=origin), destination=Endpoint(node_id=destination), **kwargs
    )


def test_risk_detour_has_real_tradeoff(graph):
    result = graph.compare(request())
    fastest, risk = result["routes"]
    assert risk["risk_exposure"] < fastest["risk_exposure"]
    assert risk["duration_min"] > fastest["duration_min"]
    assert result["explanations"]


def test_zero_risk_weight_matches_fastest(graph):
    result = graph.compare(request(risk_aversion=0))
    assert result["routes"][0]["edge_ids"] == result["routes"][1]["edge_ids"]


def test_closures_and_unreachable(graph):
    scenario = graph.dataset.scenarios[0]
    req = request(closed_edge_ids=scenario.closed_edge_ids)
    result = graph.compare(req)
    assert all(
        not set(r.get("edge_ids", [])) & set(scenario.closed_edge_ids) for r in result["routes"]
    )
    isolated = graph.compare(request(closed_edge_ids=graph.dataset.scenarios[1].closed_edge_ids))
    assert all(r["status"] == "unreachable" for r in isolated["routes"])


def test_origin_equals_destination(graph):
    result = graph.compare(request(destination="n2_0"))
    assert result["routes"][0]["duration_min"] == 0
    assert len(result["routes"][0]["geometry"]["coordinates"]) == 2


def test_invalid_endpoint_and_closure(graph):
    with pytest.raises(ValueError, match="Unknown node"):
        graph.compare(request(origin="not-a-node"))
    with pytest.raises(ValueError, match="Unknown closed edge"):
        graph.compare(request(closed_edge_ids=["not-an-edge"]))
    with pytest.raises(ValueError, match="2 km"):
        graph.resolve(Endpoint(lat=0, lon=0))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 6])
def test_invalid_risk_weight(value):
    with pytest.raises(ValidationError):
        request(risk_aversion=value)


def test_coordinate_snapping(graph):
    node = graph.nodes["n2_0"]
    result, distance = graph.resolve(Endpoint(lat=node.lat + 0.0001, lon=node.lon))
    assert result == node.id
    assert 10 < distance < 12


def test_vehicle_limits_and_parallel_edges(graph):
    req = request("n2_2", "n2_3", vehicle="heavy")
    heavy = graph.compare(req)["routes"][1]
    light = graph.compare(request("n2_2", "n2_3", vehicle="light"))["routes"][1]
    assert not any(":bridge" in edge for edge in heavy["edge_ids"])
    assert any(":bridge" in edge for edge in light["edge_ids"])


@pytest.mark.parametrize("weather", ["normal", "heavy_rain"])
@pytest.mark.parametrize("vehicle", ["heavy", "emergency", "light"])
def test_custom_astar_matches_independent_dijkstra(graph, weather, vehicle):
    rng = random.Random(26002)
    node_ids = list(graph.nodes)
    for _ in range(25):
        source, target = rng.sample(node_ids, 2)
        req = request(
            source,
            target,
            weather=weather,
            vehicle=vehicle,
            risk_aversion=rng.choice([0, 0.5, 1.5, 5]),
            closed_edge_ids=rng.sample(list(graph.edges), 5),
        )
        closed = set(req.closed_edge_ids)
        for mode in ("fastest", "risk_aware"):
            independent = nx.MultiDiGraph()
            independent.add_nodes_from(graph.nodes)
            for e in graph.edges.values():
                if graph.allowed(e, req, closed):
                    independent.add_edge(e.u, e.v, key=e.id, weight=graph.edge_cost(e, req, mode))
            actual = graph.search(source, target, req, mode)
            try:
                expected = nx.dijkstra_path_length(independent, source, target)
            except nx.NetworkXNoPath:
                assert actual is None
            else:
                assert actual is not None
                assert actual.cost == pytest.approx(expected, rel=1e-10)
                cursor = source
                for edge_id in actual.edge_ids:
                    edge = graph.edges[edge_id]
                    assert edge.u == cursor
                    cursor = edge.v
                assert cursor == target


def test_direction_and_unknown_restrictions():
    edge = Edge(
        id="ab",
        u="a",
        v="b",
        name="One way",
        length_m=10,
        speed_kph=20,
        geometry=[(91, 26), (91.001, 26)],
        risk_data_known=False,
    )
    dataset = Dataset(
        id="test",
        title="test",
        region="test",
        source="test",
        generated_at="test",
        hazard_source="unknown",
        is_synthetic=True,
        limitations=[],
        nodes=[Node(id="a", lat=26, lon=91), Node(id="b", lat=26, lon=91.001)],
        edges=[edge],
        default_origin="a",
        default_destination="b",
    )
    graph = RoadGraph(dataset)
    assert graph.compare(request("b", "a"))["routes"][0]["status"] == "unreachable"
    normal = graph.compare(request("a", "b"))["routes"][0]
    assert normal["unknown_restriction_segments"] == 1
    assert normal["unknown_risk_segments"] == 1
    assert (
        graph.compare(request("a", "b", strict_vehicle=True))["routes"][0]["status"]
        == "unreachable"
    )


def test_scenarios_do_not_mutate_shared_graph(graph):
    before = graph.dataset.model_dump_json()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(
                graph.compare,
                [
                    request(),
                    request(weather="heavy_rain"),
                    request(closed_edge_ids=graph.dataset.scenarios[1].closed_edge_ids),
                    request(),
                ],
            )
        )
    assert results[0]["routes"][1]["edge_ids"] == results[3]["routes"][1]["edge_ids"]
    assert before == graph.dataset.model_dump_json()


def test_graph_version_is_independent_of_node_and_edge_order(graph):
    reordered = graph.dataset.model_copy(
        update={
            "nodes": list(reversed(graph.dataset.nodes)),
            "edges": list(reversed(graph.dataset.edges)),
        }
    )
    assert RoadGraph(reordered).version == graph.version


def test_graph_version_ignores_float_serialization_noise(graph):
    first = graph.dataset.edges[0]
    coordinates = list(first.geometry)
    lon, lat = coordinates[1]
    coordinates[1] = (lon, lat + 1e-12)
    changed_edge = first.model_copy(update={"geometry": coordinates})
    changed = graph.dataset.model_copy(
        update={"edges": [changed_edge, *graph.dataset.edges[1:]]}
    )
    assert RoadGraph(changed).version == graph.version
