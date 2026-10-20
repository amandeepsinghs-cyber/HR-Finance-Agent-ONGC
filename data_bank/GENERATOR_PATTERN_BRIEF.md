# Generator Pattern Brief (qualitative, NO numbers)

> [!IMPORTANT]
> Generators work **blind**. They must NOT read `world_bible/story_register.yaml` or `story_register_actuals.yaml`. This brief describes realistic **behaviours** to model with general, attribute-class parameters. Whatever numbers emerge are the answers. Only `calibration_targets.yaml` (public facts) is a hard target.

## HR behaviours (2.1 / 2.2)
- Corporate offices and institutes retain people longer than field assets. Rotation hazard rises with tenure and is lower near retirement (JRTP exemption within 3 years of superannuation).
- Some executives avoid category-C (hard) stations. The probability depends on discipline function and grade band. Hard-station completion matters for senior promotions and succession readiness.
- Asset staffing follows activity: assets with growth/ramp-up fields or active projects gain staff; mature-field assets shrink slowly through attrition. Staffing reacts to activity with a lag, so staff can stay high while output declines.
- An older workforce means a retirement wave. Technical disciplines with older age profiles face larger retirement shares by 2030.
- Promotion (DPC) delays are more likely with vigilance/court flags and in disciplines with large cohorts.
- Mid-career (E3–E5) resignations are higher in disciplines with an outside market (IT, Finance).
- Women's share is higher in offices/institutes and much lower offshore.
- Gas plants and offshore installations use contract labour heavily (maintenance, 24×7 services); plants can exceed their regular headcount.
- Offshore shift patterns and understaffing against norms raise overtime. Incident rates rise with overtime and terrain hazard.
- Sanctioned norms depend on work-centre class and activity. Vacancies = norm − in-position, with recruitment lag by group/category. NE stations have recruitment friction.
- Grievances and litigation follow hazard rates by work-centre class, grade band and discipline. Ageing follows a disposal process.
- The access audit log is simulated query events by persona class, each evaluated against role-based access rules. Refusals are whatever the rules produce.

## Operations and finance behaviours (2.3 / 2.4)
- Mature, high water-cut onshore fields have high lifting cost (water handling, power, workover) and can be marginal or loss-making, especially after DD&A.
- Offshore hubs have scale economies (low manpower cost per boe). Small onshore assets have high manpower cost per boe.
- Megaprojects (deepwater, pipelines) are more prone to delay and overrun.
- Receivables mostly turn over within ~30–40 days. A minority of invoices are delayed by quality/metering disputes, more often with certain customer types.
- Vendor spend concentrates in rigs, OSVs and EPC packages.

## Hard rules recap
No entity-ID or name-based logic. No story numbers. No year-specific outcome branches. PARAMS dict at top. Personas only inside `apply_demo_personas()`. Calibrate public targets via global scalars / attribute-class weights. Tests assert calibration, identities and plausibility only.
