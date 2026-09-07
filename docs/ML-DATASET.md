# ML dataset foundation

`backend/scripts/build_ml_dataset.py` creates `datasets/processed/ml/landslide-training.csv` from the curated Northeast landslide records.

The output is a labelled starter table, not a trained model. Every row keeps the source URL, coordinates, event date, location accuracy and original trigger/size fields. Events before 2015 are assigned to `train`; events from 2015 onward are held out as `validation` to reduce temporal leakage.

Before using a predictive model in routing, the team must add negative road-day examples, join weather and road features by timestamp/location, review road matching, and report calibration, false alerts and missed disruptions. The current rule-based route risk remains the production-safe fallback.
