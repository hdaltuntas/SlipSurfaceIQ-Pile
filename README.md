# SlipSurfaceIQ Pile

**A Python library for axial pile capacity, group action, settlement and rock sockets.**

The calculation core uses NumPy and SciPy. Plotting and PDF reports are optional extras. The package was extracted from SlipSurfaceIQ-Suite and shares its `slipsurface` namespace.

## Scope

- Bored and driven piles in layered soil, including effective stresses, shaft resistance, base resistance, pile weight and buoyancy.
- Single-pile and group capacity, efficiency and block failure; single-pile and group settlement.
- Axial pile forces from the vertical force and overturning moments on a rigid cap, with compression and uplift checks. This seismic load case is not a lateral pile or dynamic soil–structure analysis.
- Rock-socket side and base resistance, minimum socket embedment, settlement and optional overburden shaft resistance.
- SPT-derived profiles with laboratory precedence and parameter provenance.
- Independent analysis of multiple borehole logs, with the unfavorable log identified for each check and one common recommended geometry.
- Whole-metre length selection and constrained length/diameter cost optimization.

The supplied configurations are examples. The methods and their assumptions need project-specific review; passing the automated tests does not establish validation for every site, soil type or design standard. See [Methods and validation](docs/METHODS_AND_VALIDATION.md) and [Changes](CHANGELOG.md).

## Installation

Python 3.10 or later. From a source checkout:

```bash
python -m pip install -e .
python -m pip install -e ".[plot]"    # add figures
python -m pip install -e ".[report]"  # add figures and PDF reports
```

For a published release, the distribution name is `slipsurfaceiq-pile`, with the same `[plot]`, `[report]` and `[all]` extras. Without these extras, analysis still works; a request for an unavailable figure/report raises `MissingDependency` with installation instructions.

## Public API and units

Use `pile.analyse(cfg)` as the common entry point. It dispatches by `pile_type` and the presence of `boreholes`:

| Input | Returned object | Main result fields |
| --- | --- | --- |
| `pile_type="bored"` or `"driven"`, one profile | `PileAnalysis` | `checks`, `Q_all`, `group`, `settlement`, `required_length` |
| `pile_type="socket"`, one profile | `SocketAnalysis` | `checks`, `Ls_check`, `Ls_req_continuous`, `Ls_design`, `design_checks` |
| Any supported pile type with `boreholes` | `BoreholeAnalysis` | `checks`, `boreholes`, `required_length`, `design_checks`, governing-log fields; socket envelopes use total pile length |

`pile.analyse_socket(cfg)` remains available for socket-specific callers and also supports multiple boreholes. Each returned object exposes `.config` and `.results`. A `BoreholeAnalysis` additionally exposes complete individual objects in `.analyses[name]`.

| Quantity | Unit/convention |
| --- | --- |
| Length, depth, diameter and spacing | m |
| `loading.Q` | kN on the **whole pile group**; per-pile load when the group is 1 × 1 |
| `socket.Q` | kN on the socketed pile |
| Moments | kN·m |
| Soil strengths and stresses | kPa |
| Soil/rock/concrete elastic moduli and rock UCS | MPa |
| Unit weights | kN/m³ |
| Friction angles | degrees |
| Settlement `s` returned by the calculation | m |
| `criteria.s_allow` and settlement check `actual`/`allowable` | mm |
| SPT energy ratio, fines, water content, LL and PL | percent |

### Soil-pile analysis

```python
from slipsurface import pile

cfg = pile.default_config("bored")
cfg["pile"].update(D=1.0, L=18.0)
result = pile.analyse(cfg)

for name, check in result.results["checks"].items():
    print(name, check["status"], check["utilisation"])
print("Recommended length, m:", result.results["required_length"])
```

A check's `utilisation` is demand divided by the corresponding limit; values above one fail. Inspect every active check, not only a capacity or factor-of-safety field. `N/A` marks an inactive check. Unavailable or invalid evaluations are not successful designs.

For soil piles, the current tip must be within the supplied soil profile. Length searches stop at the profile depth minus pile-head depth. In a multi-log analysis, the shortest available profile limits the common soil-pile search.

### Recommended lengths use whole metres

Entered lengths may be fractional and are checked at the entered geometry. **Recommended** lengths use 1 m increments and are re-evaluated at the actual proposed length. If a continuous calculation suggests 10.22 m, 11 m is a candidate; it is recommended only if all required checks pass there. Otherwise the search continues to another passing integer, if one exists. A longer pile is not assumed to improve every check in layered ground or under settlement constraints.

For soil piles, `required_length` is the first passing whole metre, starting at `ceil(criteria.L_min)`. For multiple logs, the same candidate must pass all active checks in every log. For a multi-log socket design, that integer candidate is the **total head-to-tip pile length**; the socket embedment in each log follows from its rock level and may be fractional. These derived embedments are geometry values, not separate length recommendations. `criteria.L_step` remains a recognized configuration field for compatibility but does not change this 1 m recommendation increment.

If no candidate passes in the search range, the recommendation is `NaN` and the results contain a warning. Check it with `math.isfinite()` before using it. `analyse(..., with_length=False)` checks the entered soil-pile geometry without running its length search.

### Rock-socket analysis

```python
from slipsurface import pile

cfg = pile.default_config("socket")
cfg["socket"].update(D=1.0, Ls=10.22, Q=1000.0)
result = pile.analyse(cfg)
assert isinstance(result, pile.SocketAnalysis)

print("Entered length checked, m:", result.results["Ls_check"])
print("Continuous capacity diagnostic, m:", result.results["Ls_req_continuous"])
print("Recommended whole-metre length, m:", result.results["Ls_design"])
print("Checks at entered length:", result.results["checks"])
```

For a single `SocketAnalysis`, `Ls_req` and its explicit alias `Ls_req_continuous` are continuous **capacity-only diagnostics**, not construction recommendations. `Ls_design` is the whole-metre socket-embedment recommendation after capacity, settlement and minimum socket-length checks. `design_checks` records the checks at that recommendation; `checks` records the entered/check geometry. The minimum socket ratio is at least 3D. An entered shorter socket fails the minimum-length check even if its calculated capacity is adequate. Multi-log socket results instead recommend a common total pile length, as described below.

Set `socket.Ls=0` for automatic sizing. The socket-embedment search currently stops at 60 m in each log; this is a search bound, not a statement that the methods are validated to that length. Soil-pile optimizers reject socket configurations; use the socket analysis and its single-log `Ls_design` or multi-log `required_length` result.

## Soil profiles from SPT logs

One log, supplied as a dictionary or one-item sequence, returns an `SPTProfile`:

```python
from slipsurface import pile

borehole = {
    "name": "BH-1", "water_depth": 2.0, "energy_ratio": 45,
    "records": [
        {"depth": 1.5, "N": 6, "uscs": "SM", "fines": 28, "gamma": 18.2},
        {"depth": 3.0, "N": 3, "uscs": "CL", "LL": 38, "PL": 20, "w": 32, "cu": 30},
        {"depth": 4.5, "N": 4, "uscs": "CL", "LL": 42, "PL": 21, "w": 34},
        {"depth": 6.0, "N": 5, "uscs": "CH", "LL": 55, "PL": 25, "Cc": 0.42},
        {"depth": 7.5, "N": 18, "uscs": "SP", "fines": 4},
        {"depth": 9.0, "N": 22, "uscs": "SP", "fines": 3},
        {"depth": 10.5, "N": 40, "uscs": "GW"},
        {"depth": 12.0, "N": 50, "uscs": "GW"},
    ],
}
profile = pile.derive_profile(borehole)
cfg = profile.apply(pile.default_config("bored"))
cfg["pile"].update(D=0.8, L=10.0, top=0.0)
cfg["group"].update(nx=1, ny=1)
cfg["loading"]["Q"] = 150.0
cfg["seismic"]["enabled"] = False
result = pile.analyse(cfg)
for layer, source in zip(profile.layers, profile.sources):
    print(layer["name"], layer["thickness"], source)
```

The SPT corrections are `N60 = N·(ER/60)·CB·CS·CR` and `(N1)60 = CN·N60`, with `CN = sqrt(pa / sigma_eff)` capped at 1.7. Available laboratory measurements take precedence over correlations. In particular, a measured positive `cu` below 5 kPa is preserved. The low-strength floor of 5 kPa applies only to a correlation and generates a warning.

The module uses the recorded USCS, fines and plasticity information to classify each sample. It forms intervals halfway between adjacent test depths and joins similar intervals **within the same log**. `tolerance`, `min_n_difference`, `min_thickness` and `same_depth` control this interpretation. Contradictory classifications grouped at the same depth raise an error; resolve the log or explicitly reduce `same_depth`.

Each profile retains `.name`, `.layers`, `.records`, `.sources`, `.warnings` and `.water_depth`. A missing groundwater observation produces a warning and an explicit dry assumption (`None`). Applying that profile replaces the target configuration's groundwater assumption, including when it is dry, and clears any inherited multi-log envelope. This prevents the example water table from silently replacing the log's assumption.

### Multiple boreholes: independent profiles and the unfavorable checks

Several logs return an `SPTInvestigation`, with `.profiles`, `.names` and `.warnings`. It has no combined `.layers` property. Layer strengths, soil types and groundwater levels are never averaged between boreholes.

```python
import math
from slipsurface import pile

holes = [
    {"name": "BH-sand", "water_depth": 3.0,
     "records": [{"depth": 3.0, "N": 10, "uscs": "SP"},
                 {"depth": 20.0, "N": 30, "uscs": "SP"}]},
    {"name": "BH-clay", "water_depth": 1.0,
     "records": [{"depth": 3.0, "N": 10, "uscs": "CL", "cu": 20},
                 {"depth": 20.0, "N": 20, "uscs": "CL", "cu": 80}]},
]
investigation = pile.derive_profile(holes)
cfg = investigation.apply(pile.default_config("bored"))
cfg["pile"].update(D=0.8, L=10.0, top=0.0)
cfg["group"].update(nx=1, ny=1)
cfg["loading"]["Q"] = 100.0
cfg["seismic"]["enabled"] = False
result = pile.analyse(cfg)

for key, check in result.results["checks"].items():
    print(key, check["status"], check["governing_borehole"], check["utilisation"])
length = result.results["required_length"]
if math.isfinite(length):
    print("Common recommended length:", length)
    print("Checks there:", result.results["design_checks"])
else:
    print("No common feasible whole-metre length in the supplied profiles")
```

For each check, the envelope retains the actual and allowable values from the log with the largest utilization, together with `governing_borehole`. Capacity and settlement can be governed by different logs. A failed or invalid active check in any log prevents an overall pass; a log is not discarded because another one is more favorable.

`required_length` is selected by rechecking a common integer length in every log. It is not merely the maximum of independently rounded recommendations. `results["boreholes"]` and `.analyses` preserve the individual results. All logs must have unique nonempty names. Set each water table in its own log; a scalar `water_depth=` override is rejected for a multi-log SPT investigation.

### Per-log rock conditions

Configurations can also provide separate already-defined soil profiles, water tables and rock properties. Diameter, load, installation and design choices remain common:

```python
from slipsurface import pile

cfg = pile.default_config("socket")
cfg["socket"]["Ls"] = 0.0
cfg["boreholes"] = [
    {"name": "BH-rock-a", "soil_profile": cfg["soil_profile"],
     "groundwater": {"depth": 2.0},
     "socket": {"rock_depth": 8.0, "qu": 5.0, "RQD": 50.0}},
    {"name": "BH-rock-b", "soil_profile": cfg["soil_profile"],
     "groundwater": {"depth": None},
     "socket": {"rock_depth": 12.0, "qu": 20.0, "RQD": 80.0}},
]
result = pile.analyse(cfg)
print("Common total head-to-tip length:", result.results["required_length"])
print("Actual socket embedment by log:", result.results["design_socket_lengths"])
print("Controlling checks:", result.results["design_checks"])
```

A log's `socket` section may override rock depth, strength, modulus, discontinuity and rock-mass parameters listed in `project.BOREHOLE_SOCKET_KEYS`. It cannot override shared geometry or loading. The common socket-design variable is **total pile length from head to tip**. With `overburden_i = rock_depth_i - socket.top`, each log is checked at `Ls_i = total_length - overburden_i`. Thus all logs have the same pile head and tip depths, while their actual socket embedments differ.

Multi-log socket results identify this convention with `length_basis="total_pile"`. `L` is the checked total length, `required_length` and its alias `total_length_design` are the common integer recommendation, and `checked_socket_lengths`/`design_socket_lengths` contain actual embedments by log. There is no envelope-wide scalar `Ls_design` because the embedments need not match. Fractional rock depths can produce fractional embedments under a whole-metre total-length recommendation. The envelope fields describe the common design; standalone recommendations inside individual log results are diagnostic. Rock levels and head depth are interpreted against a shared depth datum; per-log ground-elevation offsets are not modeled.

When the shared input `socket.Ls` is positive, it specifies the checked embedment at the deepest rock surface: `checked_total = max(overburden_i) + socket.Ls`. Other logs are checked with their corresponding, usually longer, embedments. `socket.Ls=0` requests automatic common-length selection. Every log must satisfy its own minimum socket length and other checks. For manually supplied log configurations, omitted groundwater/rock keys inherit the common configuration; explicitly use `groundwater.depth=None` for dry ground.

## Optimization

`optimize_length()` evaluates integer lengths in ascending order within the requested bounds. `optimize_cost()` uses constrained differential evolution with integer length and continuous diameter, minimizing `cost_a·L·D² + cost_b·L`. Its engineering feasibility constraints are separate from the cost objective, so changing monetary units does not weaken a safety constraint.

```python
from slipsurface import pile

cfg = pile.default_config("bored")
cfg["pile"].update(D=0.8, L=15.0, top=0.0)
cfg["group"].update(nx=1, ny=1)
cfg["loading"]["Q"] = 200.0
cfg["seismic"]["enabled"] = False
cfg["soil_profile"] = [
    {**cfg["soil_profile"][0], "name": "Sand", "thickness": 40.0,
     "phi": 35.0, "E": 60.0}
]
shortest = pile.optimize_length(cfg, L_bounds=(4, 30))
print(shortest["best_L"], shortest["feasible"], shortest["best_results"]["checks"])
cheapest = pile.optimize_cost(cfg, L_bounds=(4, 30), D_bounds=(0.6, 1.0),
                             popsize=6, maxiter=12, polish=False, seed=42)
print(cheapest["best_L"], cheapest["best_D"], cheapest["feasible"], cheapest["converged"])
```

Every returned geometry is evaluated again. `success` and `feasible` describe engineering feasibility; `converged` describes optimizer termination separately. A returned `best_L` with `feasible=False` is not a recommendation. Cost optimization is not a certificate of a global cost minimum. Multiple soil logs are supported through the same public analysis dispatcher.

Active checks include pile and group compression, settlement and enabled seismic compression/uplift checks, including seismic group compression. Unsupported moments on a single row of piles are rejected rather than silently ignored. Historical differential-evolution options are still accepted by `optimize_length()` for compatibility; its current search is an ordered integer scan.

## Validation and compatibility

`pile.normalize()` fills omitted configuration keys from the starter defaults, then validates supplied values. Unknown fields/method names, nonfinite values, fractional pile counts, empty profiles/log lists and invalid layers raise `PileError` (`ValueError`). Invalid layers are not deleted. Boolean inputs must be booleans or the strings `"true"`/`"false"`. `groundwater.depth=None` is the explicit dry state; `NaN` and infinity are rejected as inputs.

This is stricter than earlier releases that silently changed malformed data. Multi-log SPT callers must also migrate from a pooled `SPTProfile` to `SPTInvestigation`. See [CHANGELOG.md](CHANGELOG.md) for result semantics and other compatibility changes.

The Vesić sand-base implementation distinguishes the factor `Nσ*` multiplying **mean effective stress** from `Nq*` multiplying vertical effective stress: `Nq* = ((1 + 2K0) / 3)·Nσ*`. The reference is [USACE EM 1110-1-1905, equations 5-5b and 5-6a, worked example on printed page 5-18](https://www.publications.usace.army.mil/Portals/76/Publications/EngineerManuals/EM_1110-1-1905.pdf). The regression test uses that published example; details and limitations are in [Methods and validation](docs/METHODS_AND_VALIDATION.md).

## Figures and reports

For one soil-pile result, select figures from `available_figures(result)`:

```python
from matplotlib.figure import Figure
from slipsurface import pile
from slipsurface.pile.plotting import Plotter, available_figures
from slipsurface.pile import report

result = pile.analyse(pile.default_config("bored"))
fig = Figure(figsize=(8, 6))
Plotter(result).draw("section", fig)
fig.savefig("section.png", dpi=150)
report.export_report("report.pdf", result)
print(available_figures(result))
```

`report.export_report()` accepts the public soil-pile, socket or borehole-envelope result. For a multi-log SPT report, pass the investigation as `spt=investigation`; the report retains the separate log derivations and the common-design checks. For individual sections/plots, select the corresponding object from `result.analyses[name]`. Numerical results and their check statuses should accompany figures.

## Development and release

```bash
python -m pip install -e ".[all]" pytest
python -m pytest -q
```

GitHub Actions tests Python 3.10 and 3.12, builds the distribution and checks clean installations with and without optional extras. Current regression tests cover the USACE Vesić worked example, a separate rock-socket hand calculation, settlement and seismic gating, independent boreholes, integer recommendations and strict input handling.

Publishing is a separate operation: configure a PyPI Trusted Publisher for `publish.yml` and environment `pypi`, update the single `__version__` literal in `slipsurface/pile/__init__.py`, and push a matching version tag. The publish workflow tests and builds before uploading.

The package is under `slipsurface/pile/`; `analysis` dispatches public requests, `engine` and `socket` calculate, `spt` interprets logs, `optimizer` selects geometries, and `summary`/`plotting`/`report` present results. The distribution owns only `slipsurface.pile`, allowing other suite packages beside it.

## License

GNU Affero General Public License v3 (AGPLv3): see [LICENSE](LICENSE). Results depend on the selected methods and supplied data; no warranty is provided.
