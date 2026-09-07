# Six-person execution plan

Replace Member 1–6 with names after discussing strengths. Ownership means one accountable reviewer; everyone participates in integration and the demo.

| Member | Primary ownership | First follow-up task | Acceptance criterion |
|---|---|---|---|
| 1 | Routing engine | Review cost model and add edge snapping / turn restrictions | Independent baseline agrees on supported cases |
| 2 | Data science | Review Northeast landslide/blackspot matching and define labels | Sources, coordinate uncertainty and time split documented |
| 3 | FastAPI | Add authenticated incident reporting and immutable snapshot selection | OpenAPI contract and request isolation tests pass |
| 4 | React + R3F | Test dashboard across devices and improve map interaction | No stale routes, readable controls, accessible keyboard flow |
| 5 | Supabase + deployment | Apply migration in team project and deploy containers to a VM | Data import/export works, readiness checks pass |
| 6 | Accessibility + validation + pitch | Own closure scenarios, evaluation set and PPT | Live demo reproducible and every metric traceable |

## Shared contracts

Member 1 and Member 2 agree on score meaning and missing-data handling before tuning weights. Member 3 and Member 4 agree on API changes before merging. Member 5 versions graph snapshots with Member 2. Member 6 records results from a fixed graph and input set.

## Suggested next milestones

1. **Data review:** inspect the source inventory, identify which blackspots have usable coordinates, and choose one operational corridor with a domain mentor.
2. **Risk integration:** store observations in Supabase, review road matches, create a documented snapshot-scoring job and compare against the synthetic baseline.
3. **Accessibility workflow:** an authenticated field report creates a pending incident, a reviewer accepts it, and a closure changes route accessibility.
4. **Deployment:** validate Docker images, configure the team VM/K8s cluster and deploy one known snapshot with TLS.
5. **Validation:** test fixed journeys, partial/missing data, low connectivity and realistic disruptions. Conduct a field review before making safety claims.
6. **Pitch rehearsal:** show time-risk tradeoffs, a closure detour, an unreachable depot, real OSM data and the remaining gaps in under four minutes.

## Working practices

- One branch per feature. Keep pull requests small and include the user-visible behavior and relevant checks.
- Run an integrated demo every day. Do not leave frontend/backend integration for the final night.
- Keep secrets in `.env` or a secret manager. Do not commit raw large datasets.
- Maintain provenance for each dataset and a small reproducible evaluation fixture.
- The PPT owner updates claims from actual results. Published paper results belong in literature review, never in the prototype-results slide.

## Questions for the next team meeting

Confirm the official SIH statement wording, final project name, delivery deadline, individual strengths, demo corridor and who can provide ground-truth road status. These decisions do not block the working foundation already implemented.
