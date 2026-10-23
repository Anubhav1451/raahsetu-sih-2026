from app.model_drift import monitor_features, population_stability_index


def test_identical_feature_distribution_is_stable():
    values = [1, 2, 3, 4, 5]
    assert population_stability_index(values, values) == 0.0


def test_monitor_report_is_advisory_and_flags_shift():
    report = monitor_features({"rain": [1, 2, 3, 4, 5]}, {"rain": [40, 41, 42, 43, 44]})
    assert report["advisory_only"] is True
    assert report["features"]["rain"]["status"] == "alert"
