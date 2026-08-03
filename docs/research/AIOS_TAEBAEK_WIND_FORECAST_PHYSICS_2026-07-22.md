# Taebaek Gadeoksan Day-Ahead Wind Forecast Physics — Knowledge Receipt

- when: 2026-07-22 KST
- repo: `myworld`
- agent: Codex/OMX research team
- role: research synthesis and provider observation
- authority: recommendation-only; draft knowledge, not accepted MemoryOS memory
- evidence cutoff: public sources accessed 2026-07-22
- execution scope: no forecast was generated, no target-year data were inspected, and no operational bid was changed

## Question And Information Contract

The bounded question is which physical effects and forecast methods can improve
hourly 2025 power predictions for the 64.2 MW, 17-turbine Gadeoksan ridge farm,
especially in the score-dominant capacity-factor 0.4--0.8 region, when a bid is
issued at 13:00 KST on D-1.

The hard dynamic-data cutoff is therefore **04:00 UTC on D-1**. A nominal model
initialization time is not proof of legality: every field used at inference must
have a complete archived product and an actual publication time no later than
04:00 UTC D-1. The selected KMA LDAPS and NOAA GFS cycles are the only allowed
dynamic sources under the stated contract. Training-year SCADA may fit curves,
sector maps, analog outcomes, timing-error kernels, and calibration parameters
inside training folds; target-day observations, target-year turbine signals,
later NWP cycles, analyses, reanalyses, radar, nowcasts, realized system wind,
availability, dispatch, and price are prohibited.

The supplied 16--39 h indexing implies a candidate 00 UTC D-1 LDAPS/GFS issue,
but no immutable 2025 per-file publication or original first-ingest ledger was
provided in this workspace. The full survey therefore marks both 00 UTC sources
`reject until timestamp-proved`; cadence documentation alone cannot prove that
every required field and lead existed by a historical cutoff. A whole 18 UTC
D-2 issue is a legal fallback only when its own completeness and timestamps pass
the same predicate. The ramp-phase package freezes a ±3 h timing support and therefore
requests same-cycle padding around the 24 target hours. Missing padding truncates and
renormalizes the timing kernel; it never permits cycle splicing or adjacent-day
observations.

## Grounded Decision

The main opportunity is not another deterministic model of the same hub-wind
estimate. The user's established cross-year diagnosis says the remaining error
in 8--14 m/s flow is largely non-transferable noise and that very different ML
models are already about 0.97 correlated. At this lead, physical variables are
most valuable when they (a) identify forecast phase uncertainty, (b) construct a
conditional distribution, or (c) impose a rotor/terrain/array conversion that is
stable across blocked years. Spectacular but poorly timed local phenomena should
usually widen or condition uncertainty, not receive a signed power correction.

The ranked package names for the full survey are:

1. **Regime-conditional analog distribution plus settlement-utility decision.**
   Build an analog/quantile distribution from issue-time LDAPS/GFS trajectories,
   fit and calibrate it wholly within each training fold, then choose the point
   forecast that maximizes the organizer's exact generation-weighted 6%/8%
   band utility. This attacks the scoring rule directly instead of optimizing a
   conditional mean through a steep nonlinear curve.
2. **Front/ramp phase-error scenario ensemble.** Detect forecast fronts and ramps
   from same-issued-cycle pressure, thermal-gradient, wind, and tendency fields;
   learn a regime- and lead-conditional timing-error distribution from training
   years; marginalize power over shifted trajectories. Keep a deterministic
   time shift only if its sign transfers across blocked years.
3. **Actual-elevation, terrain-regime, settlement-group MOS.** Represent both
   model AGL coordinates and each turbine's real MSL rotor coordinates, including
   model-versus-actual terrain-height error. Condition a hierarchically shrunk
   group correction on ridge-normal flow, pressure gradient, sector, stability,
   and a Froude-like blocking indicator. A pooled static ridge-speedup scalar is
   specifically rejected.
4. **Rotor-equivalent, stability- and turbulence-aware power conversion.**
   Interpolate native model-level wind, temperature, humidity, and pressure over
   turbine-specific rotor slices; compute area-weighted rotor-equivalent speed,
   density equivalence, shear, veer, Richardson/inversion and low-level-jet
   overlap features; use a calibrated wind distribution to compute expected
   power through the saturated turbine curve. Kilometer-scale NWP gust/TKE is a
   turbulence proxy, not turbine-scale TI.
5. **Direction-uncertain wake and group-loss map.** Start with Gaussian/FLORIS
   geometry, then learn training-only group and turbine sector-loss ratios in
   2--5 degree direction bins and 6--14 m/s speed bins. Convolve the loss map
   with the forecast-direction error distribution rather than applying a narrow
   deterministic wake sector. External wakes require neighbor geometry and a
   persistent held-out sector signature.

Blade icing is the conditional challenger to rank 5: it should replace wakes
only if at least two independent winters show a recurring cold-cloud/wet-snow
accretion and persistence signature with blocked-year high-generation benefit.
Air density remains physically valid but is already in the baseline, so its
incremental rank is low.

## Strict AI-Weather Chronology

Under the stated **LDAPS + GFS only** rule, AIFS, GenCast/WeatherNext, Aurora,
Pangu-Weather, and GraphCast are excluded from deployable inference. They may be
research comparators only.

Even if that source rule were relaxed, the 04:00 UTC cutoff changes the apparent
lead. Official ECMWF and WeatherNext dissemination schedules put complete 00 UTC
products after the cutoff (for example, about 06:30--08:05 UTC depending on
product). The latest complete cycle at 04:00 UTC D-1 is therefore normally
**18 UTC on D-2**, not 00 UTC on D-1. For the 24 local target hours this is about
**21--44 h lead**, not the LDAPS/GFS 16--39 h framing. This issue-time shift must
be encoded in any fair comparison.

No current public evidence establishes that a roughly 0.25-degree global AI
model materially beats 1.5 km LDAPS for 87--120 m inflow at one Korean mountain
ridge. AIFS Single is the most credible deterministic synoptic/phase comparator;
GenCast/WeatherNext Gen is the more useful historical 2025 ensemble-uncertainty
comparator. Google's current 2026 documentation labels WeatherNext Gen and
WeatherNext Graph as legacy/deprecated and recommends WeatherNext 2; that current
recommendation does not make WeatherNext 2 a legal retrospective 2025 input. AIFS
Single became operational on 2025-02-25, and AIFS ENS on 2025-07-01, so neither
provides a uniform operational full-year-2025 ensemble experiment. Research
reruns initialized from hindsight analyses are not deployable evidence.

## Durable Red-Herring Conclusions

- **Katabatic/drainage flow and valley cold pools:** real nearby, but mainly a
  weak-wind/valley mechanism and poorly connected to ridge high-generation
  score hours. Reject as a signed primary correction.
- **Sea/land breeze penetration:** physically possible in the wider
  Samcheok--Taebaek region, but exact inland-ridge penetration at 16--39 h is
  weakly predictable and usually requires weak synoptic flow. Use at most as an
  uncertainty flag outside the main high-generation objective.
- **Convective outflow, gust fronts, downbursts, gravity-wave phase, and lee
  rotors:** plausible episodically; point location, amplitude, and hour are not
  reliable enough for deterministic day-ahead correction. Retain synoptic
  precursors only as spread/tail flags.
- **Heavy rain loading:** too small and inconsistent as a standalone power
  correction. Wet snow belongs in the icing-state model; rain can identify a
  convective or frontal regime.
- **Cutout/storm-control hysteresis:** important for safety and rare gross-loss
  events, but mostly above the 8--14 m/s steep region and often produces low
  realized generation, so it is not a leading weighted-score lever. Model it as
  a turbine-specific sequential availability state when forecast winds approach
  the actual control thresholds.
- **Calendar/system-wind curtailment proxies, negative-price logic, dynamic yaw,
  and blade soiling:** lack a stable legal weather-only signal for this task.
  Korea's cost-based market also makes imported negative-price heuristics a poor
  default. Persistent sector yaw offsets or slow degradation may be training-only
  calibration terms, not target-day states.
- **Full-year online WRF-LES/CFD and a global-AI replacement:** neither repairs
  upstream synoptic phase noise economically. Offline direction/stability terrain
  response libraries can be useful; an operational LES or a coarse global model
  advertised as direct ridge-wind truth is a red herring.
- **Universal steep-region bias correction:** the user's established near-zero
  cross-year regime-bias correlation is direct negative evidence. Any signed
  correction that does not survive forward blocked years must shrink to zero or
  remain uncertainty-only.

Low-level jets, inversions, stability, shear/veer, foehn/downslope flow, and
icing are not dismissed as physics. Their forecast amplitude or operational
translation is conditional, so they belong inside profiles, regime interactions,
or mixture probabilities rather than as universal additive megawatt offsets.

## Evidence Versus Inference

**Evidence:** KMA documents LDAPS as UM 1.5 km, 70 levels, four runs per day and
48 h forecast length; NOAA documents 00/06/12/18 UTC GFS products on a 0.25-degree
grid. Manufacturer pages establish V126/U136 rotor geometry and model-specific
operating/cutout differences. Taebaek-region observations and Korean mountain
studies establish strong ridge/valley heterogeneity, nocturnal top-slope wind,
downslope-wind and terrain-height-error mechanisms. The cited rotor-equivalent,
analog-ensemble, wake, icing, and mountain-wave literature establishes the
mechanisms and encodings, not their Gadeoksan effect sizes.

**User-established premise:** the high-generation error concentration,
cross-year near-noise result, systematic low-wind sector underprediction, model
correlation, and failed target-year transfer were supplied as rigorously
established diagnostics. They were not independently recomputed in this receipt.

**Inference:** the top-five order, likely incremental impact, external-wake
exposure, and whether icing should displace wakes are research judgments pending
the farm layout, exact group capacities/aggregation, complete issue-time archive,
and sealed SCADA ablations. No numeric score lift is claimed.

## Strongest Sources

All links were checked or source-registered on 2026-07-22.

- KMA numerical-model operations, including LDAPS: <https://www.kma.go.kr/super/model-manage.jsp>
- NOAA/NCEP GFS product inventory: <https://www.nco.ncep.noaa.gov/pmb/products/gfs/>
- ECMWF AIFS status, archive, resolution, and cycles: <https://www.ecmwf.int/en/forecasts/datasets/aifs-machine-learning-data>
- ECMWF AIFS ENS dissemination schedule: <https://www.ecmwf.int/en/forecasts/datasets/set-x>
- Google WeatherNext model fields/resolution: <https://developers.google.com/weathernext/guides/models>
- Google WeatherNext dissemination schedule: <https://developers.google.com/weathernext/guides/dissemination>
- Vestas V126 specifications: <https://www.vestas.com/en/energy-solutions/onshore-wind-turbines/4-mw-platform/V126-3-45-MW>
- Unison U136 specifications: <https://www.unison.co.kr/product/4MW_Platform_U136>
- Samcheok--Taebaek topographic wind observations: <https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2026.1724580/full>
- Rotor-equivalent wind, shear, and veer: <https://wes.copernicus.org/articles/5/1169/2020/>
- Delle Monache et al., analog ensemble: <https://doi.org/10.1175/MWR-D-12-00281.1>
- Bastankhah and Porte-Agel, Gaussian wake model: <https://doi.org/10.1016/j.renene.2014.01.002>
- NREL FLORIS/FLASC wake-analysis tools: <https://www.nrel.gov/wind/floris> and <https://www.nrel.gov/research/software/flasc-floris-based-analysis-for-scada-data>
- IEA Wind Task 19 cold-climate recommended practice: <https://iea-wind.org/wp-content/uploads/2021/09/2017-IEA-Wind-TCP-Recommended-Practice-13-2nd-Edition-Wind-Energy-in-Cold-Climates.pdf>
- Mountain-wave wind-energy impacts: <https://wes.copernicus.org/articles/6/45/2021/>

## Validation And Stop Condition

Keep 2025 sealed. Fit every analog library, event kernel, terrain correction,
wake map, curve, and probability calibration inside nested chronological folds.
Use outer forward-chaining blocked years as the primary transfer test; compare
against the complete existing baseline, report group-specific and aggregate
6% hits, 8%-only hits, misses, exact weighted utility, and the same metrics for
CF 0.4--0.8. Use `0.06 C_g` and `0.08 C_g` when settlement is group-specific;
do not silently substitute the plant-wide 3.852 MW and 5.136 MW bands.

Promote a signed physical correction only if it improves the median outer year,
improves a predeclared majority of eligible years, respects a predeclared
worst-year degradation cap, preserves its physical sign/regime, and adds value
over the full baseline. Otherwise shrink it to zero, keep it uncertainty-only,
or reject it. Research stops when the complete effect matrix, exactly five
recipes, issue-time ledger, source registry, leakage/physics/scoring audit, and
independent review have no material open defect. This receipt does not satisfy
that empirical gate by itself.

## Provider Observations From This Turn

1. The Autopilot planning guard produced an **allowed-path false negative**:
   `apply_patch` attempts targeting the explicitly permitted
   `.omx/state/subagent-tracking.json` were rejected in absolute, relative, and
   direct forms. Classify this as `planning_hook_allowed_path_false_negative`,
   preserve the rejection receipt, and do not respond by broadly bypassing the
   planning gate.
2. Native Architect/Critic completions initially lacked tracker completion
   stamps. The official notify-hook fallback synthesized completion events and
   reconciled the tracker with `completion_source=notify-fallback-watcher`, after
   which the consensus gate could consume the native-subagent evidence. Classify
   this as `native_subagent_completion_hook_gap_notify_recovered`; prefer the
   supported reconciliation path over hand-forged consensus records.
3. Native subagent completion and follow-up events repeatedly reinitialized the
   session-local Autopilot record to `deep-interview` even while the active-skill
   marker retained a later phase. Official sequential state transitions restored
   `ralplan -> ultragoal -> code-review -> ultraqa` before guarded writes. Classify
   this as `autopilot_phase_reset_on_subagent_final_state_divergence`; do not bypass
   the guard or hand-edit hook-owned activation state.

No secrets, credentials, raw provider output, private SCADA, or target-year data
are included here. No active AIOS round controller is required for this bounded
research receipt: it opens no continuing contract, dispatch, or monitor loop.
