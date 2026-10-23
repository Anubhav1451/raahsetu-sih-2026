# Disruption-label data research

Public-source review completed on 17 September 2026.

* MoRTH/NIC eDAR is the correct authoritative accident system, but its public portal requires access verification/captcha and does not expose a bulk, road-closure-labelled API for anonymous download. It must be onboarded through an authorised department export.
* data.gov.in exposes annual/state-level accident aggregates. These are useful context but have no road-segment timestamp/outcome pair, so they are deliberately excluded from supervised closure labels.
* CWC/NDMA/traffic bulletins are advisories. They become labels only after a reviewer confirms the affected road segment and outcome window.

The repository now contains a strict label schema and validator. Once an authorised export or reviewed field reports are available, ingestion can append rows without changing the model contract. Until then the disruption score remains an explicitly uncalibrated domain baseline.
