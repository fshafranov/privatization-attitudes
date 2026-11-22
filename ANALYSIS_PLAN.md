# Analysis plan: Mass privatization and political attitudes in Russia (RLMS)

**Status:** draft, 2026-11-22. Fix the plan (commit it) before estimation. Anything added or
changed after that goes in the change log (section 6) with date and reason, so what was
pre-specified and what was added later stays visible.

Decision IDs (D1, D2, ...) and robustness IDs (R1, R2, ...) are referenced from script
comments (`# ANALYSIS_PLAN.md D3`) and from `mismatch-register.csv` (`decision_id`).
`audit.py` checks that every referenced ID exists here and that every number quoted in this
file traces to a results file, so quote numbers only after a script has produced them.

## 1. Question and design
Broad question: does acquiring middle-class assets from the state make people more loyal
("more to lose") or more demanding ("protect my property from the state")? Two designs:

**Idea 1, housing privatization.** Free privatization of state flats under the 1991 law stayed
open for decades, so RLMS households switch from `c2` = unprivatized to privatized during the
panel. Design: individual fixed-effects event study of political attitudes around the household's
switch, compared with never-switchers and later switchers (staggered DiD, e.g. Callaway–Sant'Anna).
Main threat: choosing to privatize is endogenous (Plotnikova 2004: education, age and dwelling
quality predict it). Candidate exogenous variation, still to be checked: departmental housing
transferred to municipalities later; deadline extensions of the privatization law.
Prior work: Huber & Montag (2020, *Kyklos*) use privatization across countries as variation in
homeownership; Gerber & Zavisca (PONARS memo 504, 2018) find in a 2015 cross-section that
homeowners participate more and back the government more. Neither uses within-person panel
timing.

**Idea 2, losing shares.** Workers who held shares in their own enterprise (`j26`, `j28`) in the
mid-1990s and then lost them, through dilution, sale or ownership concentration (`j309`). Did
the loss change support for market reform and democrats (`j104`, `j102.3`, `j118.5`)? Comparison
groups: workers who kept their shares and workers who never held any. Prior work: Earle & Gehlbach
("A Spoonful of Sugar", Czech Republic): voucher participants who kept their shares supported
reform more. A Russian dispossession version appears untested (not yet confirmed).

## 2. Data and sample
Source: `rlms`, rounds 5–34 (1994–2025). The binding constraint is which rounds ask the political
items: the 1996 vote items exist for sure, the others are unknown. Sample rules to be set once
item coverage is tabulated.

## 3. Main specification
Descriptive pass on the 2006 round (workfile `longrun_2006`, one row per adult asked `j223`).
Linear probability models, one block per history variable because each has its own comparison
group: s1 bivariate, s2 + controls (D5), s3 + region fixed effects. Outcomes: `revise` (main),
`rich_by_crime`, `dont_know`. SEs clustered by PSU (D6). None of these estimates is causal: the
histories are recorded before the outcome but are not assigned at random.

## 4. Decisions

### D1 Outcome coding of j223
- **Stage / script:** `clean_rlms.py` phase 3; `process_longrun_2006.py` phases 1 and 3
- **Decision:** "does not know" (99999997) is kept as code 7 in cleaning. `revise` = 1 for
  "return to the state" (3) or "return to the state and privatize again another way" (4),
  0 for "leave with current owners" with or without additional payments (1, 2), missing for DK.
  DK is analysed separately as `dont_know`. Refusal or no answer (38 cases) is dropped.
- **Alternatives considered:** DK pooled with "keep" or dropped silently; an ordered scale 1–4.
- **Evidence / rationale:** DK is 13% of answers, too large to discard; options 3–4 both reverse
  current ownership, matching the "revise" grouping in Denisova et al. (2009).
- **Downstream implications:** the samples for `revise` and `dont_know` differ.
- **Status:** settled (2026-11-22)

### D2 Workplace share ownership history
- **Stage / script:** `process_longrun_2006.py` phase 2
- **Decision:** `share_owner_early` = `j26` = 1 (co-owner of employer) in any 1994–96 round,
  among people who answered `j26` then. `lost_shares` = among early owners, never `j26` = 1 in
  1998–2005 while answering `j26`; missing if not observed employed in 1998–2005.
- **Alternatives considered:** require the same employer (not identifiable without job IDs);
  use the percent owned (`j28`, too sparse).
- **Evidence / rationale:** `j26` is asked only of the employed, so "lost" mixes losing the shares
  with changing job; the item also covers business owners.
- **Downstream implications:** small samples (630–718); misclassification biases toward zero.
- **Status:** settled for the screen

### D3 Housing privatization path
- **Stage / script:** `process_longrun_2006.py` phase 2
- **Decision:** link each person to their household's `c2` in rounds 1994–2002 (via `id_h`
  within round); require at least two observations. Paths: privatized at first observation;
  became privatized (first unprivatized, last two observations privatized); never privatized;
  everything else "unclear" (excluded). Reference category = never privatized.
- **Alternatives considered:** any single switch (too noisy: reverse switches are 40-70% as common as forward
  ones, per screening/results/housing_transitions.csv); the 2025 retrospective
  item `c22` (outcome years do not overlap).
- **Downstream implications:** unclear paths excluded (count in data/logs/process_longrun_2006.log, housing_path).
- **Status:** settled for the screen

### D4 Cooperative membership
- `coop_1980s` = `j224` (2006, retrospective "were you a cooperant in the 80s?"), yes = 1, no = 0.

### D5 Controls
- Age, age²/100, female, education group (`diplom`), settlement type (`status`), log(1 + income
  in the last 30 days, `j60`). Region fixed effects in s3. Chosen as predetermined or slow-moving
  demographics; income is a possible "bad control" (it may be affected by the history), and
  s1 shows the estimate without it.

### D6 Standard errors
- Clustered by `psu`, the RLMS primary sampling unit, because respondents are sampled in
  clusters and share local conditions.

### D7 Attitude indices (2006 module)
- **Stage / script:** `clean_rlms.py` (items added; `j214_*` "nothing can be done" kept as 96);
  `process_longrun_2006.py` phase 3
- **Decision:** four indices, each the standardized mean of z-scored components (Kling, Liebman
  & Katz 2007), components signed so higher = more of the concept, z-scores against the 2006
  adult sample, at least half the components required:
  market legitimacy (j223 on a 4-point keep→return scale; rich by work, not by crime or
  connections; millionaires by hard work, not crime; not "return enterprises to the state",
  not price regulation, "no need to reduce inequality" — multi-select items coded 0/1 among
  those who answered the block); democratic values (importance of free elections, speech,
  press, opposition; agree with a two-term limit; disagree with appointed governors); trust in
  state institutions (government, Duma, courts, army, police, parties); approval of the state
  (national and regional government decisions reflect people's interests; corruption declined).
- **Alternatives considered:** Anderson (2008) inverse-covariance weights; principal components.
- **Evidence / rationale:** Cronbach's alpha and component lists are logged in
  data/logs/process_longrun_2006.log; the market index is the least coherent of the four.
- **Downstream implications:** results in SD units; indices partly overlap the single items.
- **Status:** settled (2026-11-22), not pre-specified (added after the single-item results)

### D8 Multiple testing
- Benjamini-Hochberg q-values and Holm rejections across the 20 tests of s3 × four indices × five
  history terms (`q_value_bh`, `holm_reject_05` in the results file).

### D9 Housing-wealth panel: sample and baseline tenure (trial run)
- **Script:** `process_housing_wealth.py`. Person-rounds 2006, 2012, 2017, 2018 (RLMS rounds 15,
  21, 26, 27: the rounds with the trust `j207_x` and democratic-values `j208_x` items), adults,
  observed in 2006. `owner_2006` = 1 if the household occupies its own residence (`c1` = 1) and a
  household member owns it (`c4_0` = 1); 0 if renting/dormitory (`c1` = 2, 3) or the dwelling
  belongs to non-member relatives or is not privatized (`c4_0` = 2, 3); other cases dropped.
  Tenure is fixed at 2006 so later buying and selling cannot respond to prices. People observed in
  a different PSU than in 2006 are dropped (none in practice).

### D10 Local price index
- **Decision (trial):** leave-one-household-out mean of log(self-reported market value `c1_1` /
  floor space `c6`) among owners in the same PSU and round, trimmed at the 1st/99th percentile
  of log value per m2 by round. A person's own household never enters its own index.
- **Alternatives considered:** Rosstat regional average secondary-market prices per m2 (preferred,
  external; the download failed on the certificate chain, file requested from the user);
  regional-centre prices.
- **Threat specific to this choice:** the index comes from the same survey, so local optimism or
  mood can move both the index and attitudes. The PSU-by-year fixed effects absorb anything
  common to owners and non-owners in a PSU, but not owner-specific local mood.
- **Amendment (2026-11-22):** reports more than 5x away from their PSU-round median value per m2
  are dropped. Inspecting the capitals showed unit errors that the national trim misses (St
  Petersburg 2006: lower quartile about 3,000 rub/m2; Moscow 2006: top decile above 1.3m rub/m2).
- **Status:** kept as a comparison index; the external regional price (D13) is the preferred index.

### D11 Attitude indices for the panel
- Trust index: `j207_1, 2, 3, 5, 6, 11` (government, Duma, courts, army, police, parties);
  democracy index: `j208_1, 3, 4, 5` (importance of free elections, speech, press, opposition;
  the `j209` items exist only in 2006). Items reversed so higher = more; z-scored against the 2006
  adult distribution, so changes over time are kept; mean of available z-scores, at least half needed.

### D12 Estimation and inference
- Reduced form: outcome on `owner_2006 x log local price` with person FE + PSU-by-year FE
  (s2), + age-bin-by-year FE (s3, preferred), exposure version = 2006 floor space x local price
  in rouble millions (s4), and without Moscow City and St Petersburg (s5). First stage: owners'
  own log value per m2 on the leave-out index with person and year FE.
- SEs clustered by PSU (38 clusters). Wild cluster bootstrap p-values (9,999 reps, package-default weights
  ) are computed on FWL-residualized data, because the bootstrap
  package returns a non-finite t-statistic with person fixed effects; the script asserts the
  FWL coefficient equals the FE estimate.

### D13 External regional prices
- **Scripts:** `acquire_housing_prices.py`, `clean_housing_prices.py`, `process_housing_wealth.py`.
- **Decision:** Rosstat average price per m2 on the secondary market, all flat types, end of year
  (Q4), by region, taken from statbase.ru year pages (validated exactly against Rosstat's 2021
  file for all 84 regions). RLMS PSUs are mapped to regions with
  `data/scripts/processing/psu_region_crosswalk.csv` (38 PSUs -> 32 regions; the script checks
  each mapping against the region name). Q4 prices are matched to the RLMS round of the same
  year (most interviews take place in October-December). Specifications r2-r5 mirror s2-s5 with
  `owner_2006 x log regional price`, clustered by region (32 clusters).
- **Alternatives considered:** regional-centre prices (Rosstat publishes them, but statbase's
  series is by subject); the survey-based PSU index (D10), kept for comparison.
- **Evidence:** PSU-index changes correlate 0.80 with regional price changes (analysis log).
- **Status:** settled (2026-11-23).

### D14 Annual outcomes
- **Script:** `process_annual_panel.py`. Life satisfaction (`j65`) and satisfaction with one's
  economic situation (`j66_1`), asked every year, reversed to 1 = not at all ... 5 = fully
  satisfied; generalized trust (`j206` = 1 "most people can be trusted"; asked 2006 and 2012-2025,
  so it enters only the annual design, not the event study). Person-years 2003-2018, adults
  observed in 2006, tenure fixed at 2006 (D9). These are welfare outcomes, not political ones:
  RLMS asks no political item every year.

### D15 Event study around the 2008-09 bust
- **Script:** `05_analyze_event_study.py`. Exposure = regional log change of the Q4 secondary-market
  price 2008 -> 2009 (mean -0.10, SD 0.14 across the 32 regions). Regressors: owner_2006 x
  exposure x year dummies for 2003-2013, 2007 omitted (last full pre-crisis year; RLMS 2008
  interviews fall in the crisis onset). FE: person, unit-by-year, age-group-by-year; SEs
  clustered by region. Pre-trend test: joint Wald test that the 2003-2006 coefficients are zero.
  Pooled version: owner x exposure x 1[2009-2013], 2008 dropped.
- **Alternatives considered:** exposure 2008 -> 2010 (similar ranking); boom exposure 2005 -> 2008
  (correlates -0.21 with the bust).

### D16 Regional income control
- Leave-one-out mean of log(1 + personal income last 30 days, `j60`) in the PSU-year, interacted
  with owner_2006, added to the annual design (a2) and the political four-round design (r6).
  Separates house prices from a general regional boom that may affect owners differently.
- Wild bootstrap with several regressors: the other regressors are partialled out (FWL) before
  bootstrapping; cluster codes are passed as integers because the bootstrap rejects strings.

## 5. Robustness checks
| ID | Check | Script | Status |
|---|---|---|---|
| R1 | Ordered outcome (j223 1–4) | not written | planned only if a main block shows signal |

## 6. Change log
| Date | Change | Reason | Pre-specified? |
|---|---|---|---|
| 2026-11-22 | Plan drafted | | yes |
| 2026-11-23 | Annual outcomes, 2008-09 event study, income control (D14-D16) | test pre-trends and the regional-boom confound | no |
| 2026-11-23 | External regional prices (D13) added | statbase pages collected at the user's request | no |
| 2026-11-22 | Added housing-wealth trial (D9-D12) with an internal price index | Rosstat download blocked by certificate; trial run requested | no |
| 2026-11-22 | Added four attitude indices (D7) with multiple-testing correction (D8) | single items noisy; user asked to try indices | no |
| 2026-11-22 | Switched from within-person designs to the 2006 cross-section | screening showed the political items are single-round | no |
