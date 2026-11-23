# Research state: Mass privatization and political attitudes in Russia (RLMS)

<!-- Protocol. Start of a session: read "Current state" and the last three entries of
"Session history" only. Before stopping for any reason: rewrite "Current state" (present
only, never appended to) and append one dated entry to "Session history" (never edit or
delete earlier entries). Code, results files and the registers are the source of truth:
if this file contradicts them, trust them and flag the contradiction. -->

## Current state
Last updated: 2026-11-23

- **Done:** pipeline runs end to end (`uv run python run_all.py`): clean_rlms → process_longrun_2006
  (2006 cross-section, 11,607 adults, plus four attitude indices, D7) → 01_analyze_longrun_2006
  (s1–s3, BH q-values, D8) → 02_explore_figures (fig1–fig4). Screening is in `screening/`.
- **Single items:** no 1990s history moves support for revising privatization (s3: lost shares
  0.011, SE 0.037; became privatized 0.002, SE 0.025). Lost shares → more "don't know" (0.06, SE 0.024).
- **Indices (SD units, s3):** nothing survives correction (smallest BH q = 0.267, no Holm
  rejections). Nominal hits: became privatized → democratic values +0.138 (SE 0.063); 1980s
  cooperant → state approval −0.229 (SE 0.093) and democratic values −0.261 (SE 0.123); flat
  privatized at first observation → market legitimacy +0.076 (SE 0.039). All eight housing
  coefficients are positive. Without controls, homeowners trust the state much more (+0.286, SE
  0.074, privatized at first observation), but region FE and controls remove most of that, so the
  raw "loyalty" pattern is mostly who lives where.
- **Interpretation:** at most a weak hint that owning one's flat goes with slightly more
  democratic and market-friendly views, not with more loyalty. Not causal; housing paths are
  self-selected and the region FE absorb a lot.
- **Figures:** `empirics/results/figures/fig1_coefficients.png`, `fig2_answer_mix.png`,
  `fig3_histories.png`, `fig4_indices.png`; `screening/results/fig_item_coverage.png`.
- **Data structure (checked 2026-11-22):** people link across all rounds by `idind`. Household
  `id_h` persists between consecutive rounds for about 97% of people, but is renumbered in 1995,
  2006, 2009 and 2010, so household histories should be built through people, not `id_h`. The
  2006 workfile already does this. The screening transition counts now drop the 1994->1995 pairs.
  `c1` "own residence" (about 90% every year) counts occupied state flats too; legal ownership
  is `c2` (1994-2002) or `c4`/`c4_0`.
- **Candidate housing design:** home value (`c1_1`, 2000-2025) and mortgages (`f14_71`, 2006-2025)
  against trust and democratic values (`j207_x`, `j208_x`), asked in 2006, 2012, 2017 and 2018.
  Panel support: 16,532 people answer trust in government in at least two of those rounds, and
  10,478 owners report a home value in at least two. Outside variation would have to come from
  regional house prices (Ansell 2014-style). Not built yet.
- **Housing-wealth trial (D9-D12, `03_analyze_housing_wealth.py`, figures fig5-fig7):** 6,985
  adults in at least two of 2006/2012/2017/2018, 5,354 of them owners in 2006. After the D10
  unit-error trim, PSU log price change 2006-2012 has mean 0.810 and SD 0.293 across the 38 PSUs;
  2012-2018 mean 0.089, SD 0.125. First stage: owners' own value per m2 moves 0.974 (SE 0.096)
  with the leave-out index. Reduced form (owner x log local price): person + PSU-by-year FE, trust
  index +0.069 SD (SE 0.029, wild p 0.017), democracy -0.067 (SE 0.039, wild p 0.108); adding
  age-bin-by-year FE, trust 0.035 (wild p 0.206), democracy -0.062 (wild p 0.140). Exposure
  version null. Direction "more to lose -> loyal", small, not robust to life-cycle controls. The
  internal index had unit errors (fixed by a PSU-round 5x median trim); Rosstat prices would remove
  that risk.
- **External prices (D13, 2026-11-23):** Rosstat regional Q4 secondary-market prices per m2,
  2001-2025, from statbase.ru year pages (collected at the user's request), validated exactly
  against Rosstat's own 2021 file for all 84 regions. Across the 32 RLMS regions the 2006-2012 log
  price change has mean 0.541 and SD 0.183. First stage on regional prices 0.531 (SE 0.284, wild
  p 0.107). Reduced form (owner x log regional price, clustered by region): trust index +0.090
  (wild p 0.026) with person + unit-by-year FE; +0.033 (wild p 0.392) with age-by-year FE;
  democracy index -0.075 (p 0.296) and -0.067 (p 0.340). Same signs and sizes as the survey
  index, less precise.
- **Correction (D19, 2026-11-23):** the owner x log price designs picked up a general
  owner/non-owner trend (prices rose almost everywhere). The permutation test showed it: with
  r3, permuted coefficients were centred far from zero. With owner-by-year FE (r7, preferred), the
  permutation means are about 0 and the estimates become: trust index -0.171 (wild p 0.285,
  permutation p 0.342), democracy -0.120 (wild p 0.507, permutation p 0.462), trust in government
  -0.402 (wild p 0.090, permutation p 0.100). Earlier positive "loyalty" estimates are superseded.
- **Robustness (R2, D17):** 72 baseline x year controls or LASSO-selected ones leave r7 unchanged
  (trust index -0.174 / -0.175; democracy -0.095 / -0.098); + local income: -0.130 / -0.096.
- **Second-flat households (D18):** no extra response (owners only, trust index -0.026, wild p 0.805;
  democracy -0.092, wild p 0.219); 445 people, 329 of them owners.
- **Event study with owner-by-year FE:** pre-2007 coefficients jointly zero (economic satisfaction
  p 0.634, life satisfaction p 0.352); pooled post-bust 0.060 (wild p 0.726) and -0.185 (wild p 0.440).
- **Sign diagnostics (R4):** without any price term, owners' trust relative to non-owners rose in
  2012 (trust index +0.055, p 0.074; trust in government +0.119, p 0.042) while national prices rose
  0.541 log points; the old specification read this bump as a price effect. Cross-regional price
  changes vary much less (SD 0.183-0.196) than the national change (0.541-0.607). r7 is negative in
  all 32 leave-one-region-out runs (trust index -0.230 to -0.082), but not significant.
- **Bottom line:** no evidence that housing-wealth changes moved owners' political attitudes or
  satisfaction. The only near-significant estimate (trust in government, p about 0.09) points to
  less trust, the opposite of the "more to lose -> loyal" story. Treat as a null result.
- **Status: PARKED (2026-11-23).** Published as a public GitHub repository (README with fig7). The
  user is not convinced the positive no-owner-trend estimate is spurious: owner-by-year FE also
  absorb any genuine nationwide wealth effect, so the national-time-variation reading is open.
- **If resumed:** a supply-side instrument for regional prices (pre-2006 housing completions x
  national demand) to separate housing wealth from other owner trends.

## Session history

### 2026-11-22
- Done: scaffolded the package; read the RLMS household and individual codebooks (2023 English
  versions) and the Gerber–Zavisca 2018 memo; searched OpenAlex for prior work.
- Succeeded: identified the candidate variables and the closest prior papers (Huber & Montag 2020;
  Earle & Gehlbach; Gerber & Zavisca 2018).
- Failed: could not read the round-14 questionnaire's round coverage; the codebooks do not list
  rounds per variable.
- Key decisions: none yet (no D# entries).
- Commit: no-git

### 2026-11-22 (b)
- Done: screened the RLMS household file (2,212 variables, 178,343 household-rounds).
- Succeeded: found the retrospective acquisition items `c21`/`c22` (2025 only).
- Failed: `c2` stops after 2002; the individual file is missing, so the political-item check is not run.
- Key decisions: screening kept outside the pipeline in `screening/` (pre-pipeline, not in run_all.py).
- Commit: no-git

### 2026-11-22 (c)
- Done: streamed 71 columns of the individual file (474,600 person-rounds); tabulated item coverage
  by round, share-ownership flows, and within-person overlap with housing switchers.
- Succeeded: decisive check completed; found the 2006 privatization-attitude items (`j223`, `j210_x`).
- Failed: first background stream died at start for an unlogged reason; the rerun succeeded.
- Key decisions: none (no D# entries); screening stays outside the pipeline.
- Commit: no-git

### 2026-11-22 (d)
- Done: built the pipeline (acquire = documented copy check; clean_rlms; process_longrun_2006;
  01_analyze_longrun_2006), D1–D6 in ANALYSIS_PLAN.md, raw checksum manifest; unused scaffold
  templates moved to archive/templates/.
- Succeeded: full run from raw; all history coefficients on `revise` are near zero.
- Failed: nothing; pyfixest emits pandas deprecation warnings and one multicollinearity drop in s3
  (logged in empirics/results/warnings/).
- Key decisions: D1–D6.
- Commit: no-git

### 2026-11-22 (e)
- Done: added `02_explore_figures.py` (coefficient plot, answer mix by history, trends) to run_all.py
  and a screening coverage figure; palette checked with the dataviz validator.
- Succeeded: all four figures render and were checked visually.
- Failed: nothing.
- Key decisions: none.
- Commit: no-git

### 2026-11-22 (f)
- Done: added 2006 module items to cleaning; built four KLK indices (D7); BH/Holm correction (D8);
  fig4_indices.png.
- Succeeded: indices are coherent except market legitimacy (alphas in the processing log).
- Failed: no index estimate survives multiple-testing correction.
- Key decisions: D7, D8 (not pre-specified).
- Commit: no-git

### 2026-11-22 (g)
- Done: checked household ID persistence across rounds; mapped housing variables by round; fixed
  screening transitions (dropped renumbered 1995 pairs); counted panel support for a
  home-value x attitudes design.
- Succeeded: the 2006 workfile is unaffected (links via persons within round).
- Failed: nothing.
- Key decisions: none.
- Commit: no-git

### 2026-11-22 (h)
- Done: housing-wealth trial run: cleaning extended (housing value, space, tenure); panel built
  (`process_housing_wealth.py`); first stage and reduced form (`03_analyze_housing_wealth.py`).
- Succeeded: strong first stage; owners' trust rises and democratic-values index falls with
  local prices relative to non-owners, but only the trust result with PSU-by-year FE is clearly
  significant and it halves with age-by-year controls.
- Failed: Rosstat download (certificate chain); wildboottest with person FE returns NaN t (fixed by FWL).
- Key decisions: D9-D12.
- Commit: no-git

### 2026-11-22 (i)
- Done: housing figures (fig5 local prices, fig6 first stage, fig7 reduced form, `04_explore_housing_figures.py`);
  found unit errors in self-reported home values in the capitals; added a PSU-round median trim (D10 amendment).
- Succeeded: after the trim the first stage strengthened and the reduced-form signs held.
- Failed: the earlier trial numbers (before the trim) are superseded.
- Key decisions: D10 amended.
- Commit: no-git

### 2026-11-23
- Done: collected statbase year pages 2001-2025 and Rosstat's archived 2021 regional file
  (`acquire_housing_prices.py`); parsed and validated them (`clean_housing_prices.py`); PSU-region
  crosswalk; external-price specs r2-r5 in `03_analyze_housing_wealth.py`; fig7 shows both indices.
- Succeeded: exact match with Rosstat 2021 for all 84 regions after mapping the Arkhangelsk and
  Tyumen sub-rows; results replicate the survey-index pattern.
- Failed: rosstat.gov.ru unreachable (certificate); statbase pages for 2002 and 2004 have no table.
- Key decisions: D13.
- Commit: no-git

### 2026-11-23 (b)
- Done: git initialized (5 commits on main); on branch feature/annual-event-study added annual
  outcomes to cleaning, `process_annual_panel.py`, `05_analyze_event_study.py`, the owner x local
  income control in the political design (r6), fig8; renamed the figure script 04 -> 06.
- Succeeded: pre-trend tests run; the bootstrap now works with several regressors and string clusters.
- Failed: pyfixest Wald test returns an object, not a dict (fixed); bootstrap failed on string
  cluster codes (fixed with integer codes); bootstrap p-values in s3 moved in the third decimal
  after the cluster-code change.
- Key decisions: D14-D16.
- Commit: see git log on feature/annual-event-study

### 2026-11-23 (c)
- Done: branch feature/flexible-controls: baseline characteristics and second-flat items;
  `07_robust_flexible_controls.py` (R2, LASSO post-double-selection), `08_analyze_second_flat.py`,
  `09_robust_permutation.py` (R3), `10_explore_robustness_figures.py`; owner-by-year FE (D19) added
  to all owner x price designs; fig7 now shows the corrected specification.
- Succeeded: the permutation test caught the owner-trend confound; after the fix the permutation
  distributions are centred at zero and the event-study pre-trends are clean.
- Failed: sklearn LassoCV no longer accepts n_alphas (explicit alpha grid); pandas Int64->str keeps
  NaN (missing categories fixed); nfm1_n asked of about a fifth of households (size counted instead).
- Key decisions: D17-D19.
- Commit: see git log on feature/flexible-controls

### 2026-11-23 (d)
- Done: R4 `11_robust_sign_diagnostics.py` (owner x year trend, price-variation decomposition,
  leave-one-region-out); ran it alone (4 s) and twice for byte-identical output.
- Succeeded: explains the sign flip: old estimate = owners' 2012 trend bump x national price path.
- Failed: nothing.
- Key decisions: none new (R4 documents D19).
- Commit: see git log on feature/sign-diagnostics

### 2026-11-23 (e)
- Done: README for publication; run_all logs project-relative paths; regional price file git-ignored;
  history rewritten (no-reply author email; price file and old logs with home paths removed); pushed
  to a public GitHub repository.
- Succeeded: see git log; project parked.
- Failed: nothing.
- Key decisions: price data not redistributed (user, 2026-11-23).
- Commit: see git log
