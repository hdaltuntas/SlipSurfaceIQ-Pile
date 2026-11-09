# Changelog

## Unreleased

### Calculation and acceptance corrections

- Corrected the Vesić sand-base factor expression and the distinction between the `Nσ*` factor for mean effective stress and `Nq*` for vertical effective stress. Added the USACE EM 1110-1-1905 worked-example regression; previous results using the affected formulation should be recalculated.
- Included settlement and enabled seismic group-compression checks in soil-pile length selection and optimization.
- Made minimum socket length and settlement mandatory for the combined socket acceptance status. Preserved the capacity-only status separately.
- Kept entered fractional lengths for exact analysis while selecting recommended lengths on a 1 m grid and checking the actual proposed geometry. A rounded candidate is not automatically considered feasible.
- Kept single-log socket capacity diagnostics in `Ls_req` and `Ls_req_continuous`; single-log `Ls_design` is the checked whole-metre embedment recommendation.
- Replaced cost-scaled feasibility penalties with a separate engineering constraint in cost optimization. Engineering feasibility and optimizer convergence are reported separately, and final geometries are re-evaluated.

### Independent borehole analysis

- Added public dispatch through `pile.analyse()` for bored, driven, socket and multi-log analysis.
- Added `SPTInvestigation` for multiple SPT logs. Each log retains its own strata, sample provenance and groundwater; no cross-log averaging or majority-vote geology is performed.
- Added a check-by-check unfavorable envelope that identifies its governing borehole and retains the actual and allowable values from that log.
- Added one shared whole-metre recommendation evaluated in every log. For multiple rock-socket logs, the design variable is total head-to-tip pile length, with actual socket embedment derived separately from each log's rock level and properties.
- Rejected duplicate/empty log names, invalid logs and attempts to override shared geometry or loading through an individual log.
- Restricted soil-pile entered tips and recommended lengths to the available profiles; the shortest log bounds the common search.

### Input and SPT corrections

- Supplied invalid method names, nonfinite values, fractional pile counts, empty profiles/logs and invalid layers now raise clear errors. Invalid layers are no longer silently removed.
- Boolean strings `"false"` and `"true"` are parsed explicitly; arbitrary truthy strings are rejected.
- `groundwater.depth=None` explicitly represents dry ground. Applying an SPT profile preserves its dry/groundwater state and removes a stale inherited multi-log envelope.
- Preserved positive laboratory `cu` values below 5 kPa. The 5 kPa floor applies only to a correlation and generates a corresponding warning.
- Added finite/range checks to SPT measurements, metadata and derivation options; conflicting coincident classifications within one log raise an error.

### Compatibility notes

- `derive_profile(one_log)` and a one-item sequence still return `SPTProfile`. Several logs now return `SPTInvestigation`; use `.profiles` or `.apply(cfg)` instead of assuming one merged `.layers` list.
- `normalize()` still supplies omitted starter defaults, but explicitly invalid data is rejected instead of repaired silently.
- `criteria.L_step` remains recognized for compatibility; recommended lengths use 1 m increments. Historical differential-evolution arguments to `optimize_length()` remain accepted, but the length-only algorithm now performs an ordered integer scan.
- Socket `check["status"]` now covers all acceptance checks. Use `check["capacity_status"]` when the capacity-only outcome is specifically needed.
- A multi-log socket envelope uses `length_basis="total_pile"`, `required_length`/`total_length_design`, and per-log `checked_socket_lengths`/`design_socket_lengths`. It has no scalar `Ls_design`. Positive shared input `socket.Ls` describes the checked embedment at the deepest rock; other embedments follow from the same total pile length. Derived embedments may be fractional even though the recommended common total length is an integer.
- `success`/`feasible` describe rechecked engineering feasibility; `converged` is a separate optimizer outcome. Do not use a returned best attempted geometry as a recommendation when `feasible=False`.
- No release is implied by this unreleased changelog. See the README for the separate publishing workflow and [Methods and validation](docs/METHODS_AND_VALIDATION.md) for the scope of the numerical checks.
