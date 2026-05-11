# Role Level Calibration

Calibrate language to the role level the user is targeting. Saying "led the architecture of our platform" reads correctly for a Staff/Principal but is over-claiming for a Junior; saying "contributed to several backend services" is honest at Junior but under-claims for a Director. The same underlying work can be described at multiple levels — but only ONE of those descriptions is the most honest. Pick the level that matches the user's actual scope.

## Inferring level from a JD

Check these signals in `jd_analysis.json`:

| Signal | Level cue |
|---|---|
| "0–2 years experience" / "Junior" / "Associate" / "I" / "II" | Junior |
| "3–5 years" / "II" / "III" / "Mid-level" / "Engineer" (no qualifier) | Mid |
| "5–8 years" / "Senior" / "III" / "IV" / "Sr." | Senior |
| "8+ years" / "Staff" / "Lead" (IC) / "Principal" / "IV" / "V" | Staff/Principal |
| "10+ years" / "Director" / "Manager of Managers" / "Head of" | Director+ |
| Listed responsibilities mention "mentor", "review architecture", "set direction" | ≥ Senior |
| Listed responsibilities mention "drive cross-team alignment", "set technical strategy" | ≥ Staff |
| Listed responsibilities mention "manage team of N", "performance review" | People manager (parallel ladder) |
| Salary band $100K–$150K (US tech) | Mid/Senior |
| Salary band $200K+ (US tech) | Senior/Staff |
| Equity grant > 0.1% (early-stage startup) | Senior+ |

**These are heuristics, not rules.** Titles vary wildly across companies. Use the *responsibilities* and *required years* as primary signals; the title as a secondary signal.

## Language calibration

### Junior (0–2 years)

| Use | Avoid |
|---|---|
| "Built", "implemented", "shipped", "developed", "fixed", "tested" | "Architected", "led", "drove strategy", "owned" |
| "Contributed to", "supported", "partnered with" | "Directed", "managed" |
| "Learned", "applied" (sparingly) | "Mentored" (unless true), "set technical direction" |
| Specific tasks with concrete tech | Strategic claims |
| Education prominent (often 1-2 lines) | — |

**Bullet shape:** One specific thing you did, plus an outcome. Don't try to make it sound bigger than it was.

> "Implemented retry-with-backoff logic for our Stripe webhook handler, eliminating a recurring class of payment-sync failures."

Honest at Junior. Concrete, ownable, useful.

### Mid (3–5 years)

| Use | Avoid |
|---|---|
| "Built", "designed", "shipped", "owned" (a feature/service), "improved" | "Architected the platform" (unless true), "led the team" (without qualifying) |
| "Led the [specific scope]" — feature, service, migration | "Set strategy" (unless true) |
| "Mentored junior engineers" (if true) | "Drove org-level change" |
| Trade-off reasoning visible | Pure list-of-tasks |

**Bullet shape:** Specific scope you owned + outcome + (optional) trade-off you navigated.

> "Owned the orders service through a 4× traffic increase: redesigned the data model, added a 2-tier cache, and ran a zero-downtime migration. p99 stayed under 250ms throughout."

### Senior (5–8 years)

| Use | Avoid |
|---|---|
| "Led", "drove", "designed", "architected" (specific systems) | "Set company strategy" (unless true) |
| "Mentored", "reviewed", "set technical direction for [team/area]" | "Owned the entire platform" (unless true) |
| "Made the trade-off to X over Y because Z" — show judgment | Vague seniority signaling without evidence |
| Cross-functional partnership made explicit | — |

**Bullet shape:** Scope (team/system) + decision/trade-off + outcome. Senior bullets show judgment, not just throughput.

> "Led the Orders v2 rewrite (3 engineers, 6 months): chose event-sourced over CRUD because of audit requirements, accepting the operational complexity for a 10× simpler audit story. Shipped on time; zero data-integrity issues in 18 months post-launch."

### Staff / Principal (8+ years, IC track)

| Use | Avoid |
|---|---|
| "Defined the technical strategy for [area]" | Buzzwords ("synergized", "leveraged at scale") |
| "Authored RFCs adopted across [N teams]" | Empty leadership claims |
| "Resolved cross-team alignment on [issue]" | Pure throughput language |
| "Mentored [N] senior engineers; [outcome — e.g., 2 promoted]" | — |
| Influence patterns (writing, mentoring, system design) over individual code throughput | — |

**Bullet shape:** Cross-team scope + influence mechanism + measurable org-level outcome.

> "Authored the org's data-platform RFC adopted by 6 teams; resulting standard cut new-pipeline onboarding from 4 weeks to 5 days and eliminated 2 incident classes."

### Director+ / People Manager

| Use | Avoid |
|---|---|
| "Built and led a [N]-person team" | Individual-contributor task lists |
| "Hired [N] over [time], retention [%]" | "Coded a feature" (move to a Selected Achievements section if relevant) |
| "Set quarterly priorities for [scope]; delivered [outcome]" | — |
| "Coached [N] managers" (if applicable) | — |
| Budget responsibility, roadmap, headcount | — |

**Bullet shape:** Scope (people, budget, roadmap) + business outcome. Director resumes are read for *what the org achieved under you*.

> "Grew the Platform org from 8 to 22 engineers across 3 sub-teams over 18 months; org delivered the multi-region rollout, cut platform-caused incidents 70%, and shipped the cost-attribution layer that reduced infra spend by $1.4M annualized."

## When the user's actual work doesn't match the JD level

Three honest options:

1. **Apply anyway, with calibrated language.** Apply for a Senior role with Mid-level scope description — let the recruiter screen. Don't inflate.
2. **Apply for a level down.** If the JD is Staff and the user is Mid, apply for the equivalent Senior posting at the same company.
3. **Stretch with evidence.** If the user has *some* of the level signals (e.g., owned a specific cross-team initiative), surface that bullet prominently. But don't manufacture additional signals.

**Never inflate the language to match the JD level if the underlying work doesn't support it.** Recruiters see hundreds of resumes and have well-calibrated bullshit detectors. Inflated bullets fail the interview.

## Calibrating across the whole resume

A resume's overall "level vibe" comes from the *consistency* of bullet calibration. One Staff-level bullet surrounded by Junior-level bullets reads as a fluke. Five consistent Senior-level bullets reads as a Senior.

If the user is at the boundary between two levels, calibrate to the **lower** level — it's safer. Recruiters more often promote candidates upward in screening ("Looks Senior+, let's interview at Staff") than downward.
