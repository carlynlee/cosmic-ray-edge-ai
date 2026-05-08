# Email Drafts

---

## 1. Update to Harvey / Spencer / Wu — RINO/transformer approach
**To:** Harvey Newman, Spencer, Wu  
**Status:** Draft (Happy New Year context)

RINO paper author Zichun recommended:
- CREDO images → DINO-v2/v3 vision transformers, leverage Meta pre-trained models directly
- CosmicWatch event sequences → BERT/GPT-style transformers, treat each event as a token
- Multi-modal fusion (combine both into unified embedding space) — longer-term exploration

Rough implementation of foundational modules underway. RINO framework used as inspiration, not direct adoption.

---

## 2. Reply to Harvey — flyer feedback + undergrad funding paths
**To:** Harvey Newman  
**Subject:** Re: Draft flyer for CPP student recruiting

Key points:
- Will add per-track prerequisites to flyer so students can self-qualify
- **SURF 2027:** target a clean cycle (applications open October), propose federated-learning-on-distributed-detectors track, draft for Harvey's review later this summer
- **Summer 2026:** ask Harvey to co-pitch one industry sponsor at $8k/10-week rate — Internet2, HPE, or NVIDIA are thematically aligned; a joint note would carry more weight
- SURF 2027 proposal should name Harvey as Caltech faculty sponsor and Yifan as CPP collaborator

---

## 3. Caltech undergrad recruitment announcement
**To:** Harvey Newman (for review), then Caltech undergrads  
**Subject:** Undergraduate research opportunity: distributed cosmic ray sensor networks

Recruiting undergrads at any level for: CosmicWatch detector instrumentation, real-time data pipelines, CREDO image analysis, transformer self-supervised learning, multi-modal ML, federated learning.

Participation paths:
- Research units during academic year
- SURF 2027 → possible senior thesis
- Summer 2026 pilot only if industry sponsorship secured

Students should send year, relevant experience, and area of interest (hardware / data systems / ML / physics).

---

## 4. Note to Harvey + Yifan — HPC4EI DOE solicitation
**To:** Harvey Newman, Yifan  
**Subject:** HPC4EI solicitation — possible fit for Oligo Space?

DOE HPC4EI program: up to **$400k** in national-lab HPC + staff support, 20% industry cost share.  
**Concept paper due: May 27, 2026.**

Two possible areas:
- **AMMTO** (materials/manufacturing): HPC+ML for detector component qualification or radiation-environment hardware
- **ITO** (industrial/grid-edge): distributed sensing + ML for industrial infrastructure or data-center energy

Open questions for Harvey and Yifan:
- Is Oligo Space an appropriate industry lead?
- Which area is the better technical fit?
- Can the CosmicWatch/CREDO/federated-learning work be reframed without stretching it?
- Is there a natural DOE lab collaboration angle?

Timeline is short — need a quick sanity check before investing time in a concept paper.

---

## 5. Bug report to Slawek — credo-data-exporter.py
**To:** Slawek (CREDO project)  
**Re:** `credo-data-exporter.py` export files never becoming available

**Problem:** Script hangs waiting for S3 export files that return 404 or 403 (NoSuchKey). Script only handles 404, so 403 falls through and crashes.

**Suggested fixes:**
1. Handle both 404 and 403 (check XML body for `<Code>NoSuchKey</Code>`) when polling for export readiness
2. Fix incorrect print message ("mapping export" should say "data export")
3. Add reasonable max retry limit / timeout

Offered to submit a PR with the fixes.
