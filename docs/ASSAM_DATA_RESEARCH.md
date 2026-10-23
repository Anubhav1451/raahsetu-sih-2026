# Assam public-data acquisition findings

Research date: 2026-09-17

## Useful official sources

- [ASDMA Assam flood reports](https://asdma.assam.gov.in/information-services/assam-flood-report) — official flood situation reports and DRIMS context; useful for dated flood evidence, but individual road-segment labels still require extraction and review.
- [Assam PWD Roads road-safety records](https://pwdroads.assam.gov.in/portlets/road-safety) — publishes black-spot locations, road names and coordinates; useful for geocoding/segment candidates, not disruption outcomes by itself.
- [Assam PWD SDRF road restoration](https://pwdroads.assam.gov.in/schemes/state-disaster-response-fund-sdrf) — documents flood-damaged road/bridge restoration categories and official repair records.
- [ASDMA 2024 flood memorandum](https://asdma.assam.gov.in/sites/default/files/swf_utility_folder/departments/asdma_revenue_uneecopscloud_com_oid_70/menu/document/assam_flood_memorandum_2024_.pdf) — dated flood context and affected districts; aggregate context, not automatically a road-segment label.
- [ASDMA annual activity report](https://asdma.assam.gov.in/sites/default/files/swf_utility_folder/departments/asdma_revenue_uneecopscloud_com_oid_70/menu/document/annual_activity_report-asdma-4.pdf) — includes highway damage/restoration examples such as NH-15, NH-154 and NH-44; each record still needs segment/time/outcome review.

## What can be added safely

- Source registry entries and candidate advisories with the official URL, publication date and extracted road text.
- Road-segment candidate matches from published coordinates, clearly marked `pending_review`.
- Evidence links for the operator review queue.

## What cannot be claimed yet

- A black spot is not automatically a disruption label.
- A district-level flood report is not proof that a specific road segment was closed.
- Restoration funding or project records do not establish closure start/end times.
- No Assam negative control is promoted without an official open/passable observation and reviewer confirmation.

## Remaining Assam manual gate

For each candidate, an authorised reviewer must confirm exact graph segment, event time, status (open/restricted/blocked), source evidence and review identity. Only then can it enter the supervised training label table.
