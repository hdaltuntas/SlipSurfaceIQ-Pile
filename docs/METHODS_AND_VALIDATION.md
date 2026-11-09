# Methods and validation notes

This document records the calculation conventions affected by the current changes. It does not certify the methods for all geology, construction methods or national design codes. The defaults are example inputs, not recommended site parameters.

## 1. Vesić base resistance in sand

The implementation now distinguishes two bearing-capacity factors:

- `vesic_nsigma(phi, Irr)` returns `Nσ*`, which multiplies mean effective normal stress.
- `vesic_nq(phi, Irr)` returns `Nq*`, which multiplies vertical effective stress.

With the implemented normally consolidated-soil assumption `K0 = 1 − sin(phi)`, the relationship is:

```text
σ′o = σ′v · (1 + 2K0) / 3
Nq* = Nσ* · (1 + 2K0) / 3
qb  = σ′o · Nσ* = σ′v · Nq*
```

The reference is **US Army Corps of Engineers, EM 1110-1-1905, Bearing Capacity of Soils, 30 October 1992**, equations **5-5b and 5-6a**, with a worked example on printed page **5-18**: [official manual](https://www.publications.usace.army.mil/Portals/76/Publications/EngineerManuals/EM_1110-1-1905.pdf).

The published example uses phi = 36 degrees, reduced rigidity index `Irr = 42.6`, and vertical effective stress 2.4 ksf. Its rounded intermediate values are `Nσ* ≈ 60.7`, a mean-stress multiplier about 0.61, and `qb ≈ 88.9 ksf`. The regression in `tests/pile/test_axial.py` allows for those published rounding steps. The code computes with unrounded intermediate values.

`tip_vesic()` exposes `Nsigma`, `Nq`, `K0`, `sigma_mean`, `mean_stress_factor`, `Ir`, `Irr` and `delta` so callers can inspect the complete calculation. Its modulus input is in MPa; stresses and returned base resistance are in kPa. The function applies the existing reduced-rigidity and volume-change assumptions described in its docstring. The manual example validates a specific factor/stress calculation; it is not comprehensive validation of every correlation or input domain.

An earlier result that multiplied `Nσ*` directly by vertical effective stress omitted the mean-stress conversion. Results from that implementation must be recalculated; a changed numerical result is expected after correcting this relationship and the factor expression.

## 2. Geometry and length recommendations

The entered geometry and the recommended geometry are distinct results:

| Analysis | Entered geometry | Recommendation |
| --- | --- | --- |
| Soil pile | `pile.L`, including fractions | `required_length`, whole metres |
| One rock-socket log | `socket.Ls`, including fractions | `Ls_design`, whole metres of socket embedment |
| Multiple soil logs | The same entered length/diameter in every log | One shared integer `required_length` passing every log |
| Multiple rock-socket logs | Common total head-to-tip length; different embedments from each rock level | Integer total `required_length`/`total_length_design`, with per-log `design_socket_lengths` |

All active checks are evaluated at the proposed integer geometry. A continuous 10.22 m result does not by itself prove that 11 m is acceptable. The candidate at 11 m must pass capacity, settlement and all other applicable checks. If it fails, later integer candidates are examined within the supported search bounds; if none passes, the recommendation remains unavailable.

For soil piles, the tip must lie within the supplied profile. The common search ends at the shallowest log's available profile depth minus pile-head depth. This avoids extending one log's final soil layer to justify a longer recommended pile. Stress integrations used by the existing settlement methods can still extend the last layer below the recorded profile; that settlement-model assumption should be reviewed separately from the explicit tip/search limit.

For a single socket log, `Ls_req`/`Ls_req_continuous` report a continuous capacity threshold. They do not enforce the complete design checks. `Ls_design` additionally enforces the minimum embedment (at least 3D) and the selected settlement criterion. `checks` applies to `Ls_check`; `design_checks` applies to `Ls_design`.

For multiple rock-socket logs, the shared design variable is **total pile length from head to tip**. If log i has `overburden_i = rock_depth_i - socket.top`, the checked socket embedment is `total_length - overburden_i`. The total recommendation is an integer, while derived embedments can be fractional and are not separate recommendations. `length_basis="total_pile"` identifies this result convention; `L` is the checked total length, `required_length`/`total_length_design` is the common total recommendation, and `checked_socket_lengths`/`design_socket_lengths` map log names to actual embedments. The envelope does not provide a scalar `Ls_design`.

A positive shared input `socket.Ls` means that embedment at the deepest rock level, giving `checked_total = max(overburden_i) + socket.Ls`. Each other log is evaluated at the resulting common head and tip depths. With `Ls=0`, automatic sizing searches total length from `ceil(max(overburden_i + minimum_socket_i))` through `floor(min(overburden_i + 60))`, rechecking the actual embedment and all active checks in every log.

The socket search limit is currently 60 m. A returned `NaN` recommendation means no feasible recommendation was established within the search range; it is not a zero-length design.

## 3. Multiple boreholes

Each borehole supplies a separate geological model. SPT samples, classifications, strengths and water levels from different boreholes are never pooled into a synthetic profile. Names must be unique and are retained throughout the analysis and reporting.

At any trial geometry, every active check is evaluated for each log. The envelope selects the greatest utilization for each check and copies that log's actual and allowable values. Therefore the capacity-controlling log may differ from the settlement-controlling log. The common recommendation is searched and checked directly; taking the maximum of independent recommendations would not be sufficient when checks vary non-monotonically with length.

`SPTInvestigation.apply()` supplies independent `boreholes` to the public dispatcher. A single `SPTProfile.apply()` instead selects that log and clears any previous envelope. Missing SPT groundwater data means an explicit dry assumption plus a warning, rather than retention of the starter example's groundwater level.

For rock sockets, each log can supply its own rock surface and material properties. Common total pile length, diameter and load are enforced. Differing rock levels produce different overburden thicknesses and actual socket embedments, with corresponding shortening, weight and resistance effects. Taking one identical socket embedment in every log would place pile tips at different depths and does not represent this common-pile design. Depths are interpreted against the configuration's shared ground-surface datum; per-log elevation offsets are not modeled. The envelope's total recommendation and embedment map define the common design; any standalone recommendation retained inside an individual log's result remains a diagnostic for that log.

## 4. Checks used for acceptance

Soil-pile recommendation and optimization use the active checks for individual capacity, group capacity, settlement, seismic individual compression/uplift, and seismic group compression/uplift. Seismic calculations here distribute axial force under the supplied vertical force and moments on a rigid cap. They do not solve lateral deflection, a p–y model, a dynamic response or a structural reinforcement design.

Socket acceptance uses capacity, minimum length and settlement. A capacity pass alone does not make a too-short or excessively settling socket acceptable. `check["capacity_status"]` records the capacity-only outcome; `check["status"]` records the combined socket acceptance outcome.

An invalid or missing active check cannot be discarded to obtain a favorable borehole envelope. When interpreting results, distinguish `N/A` for an inactive check from a failed or unavailable evaluation.

## 5. Input and optimization contracts

The normalizer validates explicitly supplied values instead of replacing bad method names, dropping invalid layers or rounding fractional pile counts. Numeric configuration inputs must be finite. An explicit empty profile/log list is an error. `groundwater.depth=None` is the supported dry-state representation.

SPT input checks include finite measurements and options, compatible coincident classifications within a log, positive sample depth, nonnegative blow counts, valid classification/behavior names and compatible laboratory ranges. Positive measured clay strengths are preserved even below 5 kPa; only the low-strength correlation is subject to the warned 5 kPa floor.

Length-only optimization is an ordered integer search. Cost optimization uses an integer length, continuous diameter and a separate nonlinear engineering constraint. Each returned geometry is evaluated again. `feasible`/`success` describe the engineering checks, while `converged` describes the numerical optimization outcome. A feasible result is not a proof of global cost optimality, and a best attempted result with `feasible=False` is not a design recommendation.

## 6. Evidence and remaining scope

The test suite includes:

- The cited USACE Vesić worked example and separate checks of mean/vertical stress conversion.
- An analytical rigid-pile limit for socket settlement, checked against independently assembled shaft and base spring stiffnesses; this is not a field calibration.
- Cases in which settlement, seismic group compression or minimum socket length prevents acceptance despite another check passing.
- Separate-log identity, order invariance, groundwater separation and re-evaluation of shared integer recommendations.
- Invalid input, infeasible optimization and dependency/package installation regressions.

These checks establish behavior for the tested cases. They do not replace a broader verification matrix against independently sourced pile-load tests, documented hand calculations across the supported soil/rock domains, and applicable project design requirements. The software uses the configured methods and global safety-factor conventions; it should not be described as automatically compliant with a particular design code without a separate, documented implementation and validation of that code.
