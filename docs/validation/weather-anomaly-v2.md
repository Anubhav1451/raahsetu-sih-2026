# Weather anomaly model v2

The locked model is a state-wise, calendar-month seasonal standardized-distance detector. It uses daily precipitation, maximum wind, diurnal temperature range, and daily mean relative humidity at 2 m. The historical source is Open-Meteo's Historical Weather API / reanalysis, with one reference coordinate per Northeast state; it is not a statewide observation network.

Training is 2021-01-01 through 2024-12-31. The 2025 temporal holdout is saved in `backend/data/weather_anomaly_holdout_2025.json`. Every state records monthly baselines, p95/p99 feature thresholds, p95/p99 score thresholds, and the model/source hash in `backend/data/weather_anomaly_model.json`.

The output is an advisory anomaly score with feature contributions and provenance. It is not a landslide, road-closure, or delivery-delay probability. Routing may use the score only as a bounded weather-risk modifier; verified closures and field reports remain authoritative.
