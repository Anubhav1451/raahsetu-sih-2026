# Northeast graph audit

The audit must be generated from the current files, not copied from a prior report. For each state snapshot record node count, directed edge count, SHA-256, dataset version, provenance, graph load time and fastest/Risk-A* smoke results. A graph is labelled real only when its OSM source and extraction receipt are present; benchmark or synthetic graphs remain explicitly labelled.

Supabase stores graph metadata and import audits. Large graph payloads stay local. Assam and Tripura are expected to be the first candidates for local-only bulk storage because they exceed the free-tier budget when represented as fully expanded PostGIS edge rows.
