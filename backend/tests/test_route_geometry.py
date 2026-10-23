from types import SimpleNamespace

import pytest

from app.route_geometry import assemble_geometry


def test_curved_parallel_and_reversed_geometry_is_not_smoothed_or_mutated():
    nodes = {
        "a": SimpleNamespace(lon=91, lat=26),
        "b": SimpleNamespace(lon=92, lat=26),
        "c": SimpleNamespace(lon=93, lat=26),
    }
    first = SimpleNamespace(id="a>b:1", u="a", v="b", geometry=[(91, 26), (91.4, 26.2), (92, 26)])
    second = SimpleNamespace(id="b>c:0", u="b", v="c", geometry=[(93, 26), (92.5, 26.1), (92, 26)])
    geometry, warnings = assemble_geometry([first, second], nodes)
    assert geometry["coordinates"] == [(91, 26), (91.4, 26.2), (92, 26), (92.5, 26.1), (93, 26)]
    assert second.geometry[0] == (93, 26)
    assert warnings == []


@pytest.mark.parametrize("points", [[], [(91, 26), (float("nan"), 26)], [(91, 26), (93, 26)]])
def test_missing_invalid_or_disconnected_shape_is_rejected(points):
    nodes = {"a": SimpleNamespace(lon=91, lat=26), "b": SimpleNamespace(lon=92, lat=26)}
    edge = SimpleNamespace(id="a>b", u="a", v="b", geometry=points)
    with pytest.raises(ValueError):
        assemble_geometry([edge], nodes)
