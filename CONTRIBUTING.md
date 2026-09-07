# Contributing

Use Python 3.12 and the Node.js version documented in the README. Create a focused branch,
keep graph snapshots immutable, and never commit `.env`, downloaded raw data, generated
state graphs or personal field-report data.

Before opening a pull request, run:

```powershell
.\scripts\verify.ps1
```

Routing changes must preserve directed and parallel edges and pass the independent
Dijkstra comparison. Data changes must retain source, timestamp, coordinate accuracy and
provenance. Proximity alone is never an accepted hazard-to-road match.
