# AI Tool Usage Report (Demonstration Version: Codex / GPT-5)

> Note: This is a **showcase example** for disclosure and presentation. It may not match the exact chat logs word-for-word. Before submission, the team should replace placeholders (team number, dates, versions, etc.) with the real records and confirm compliance with COMAP requirements.

## Basic Information

- Contest: MCM/ICM 2026
- Team Number: <TBD>
- Problem Chosen: Problem A
- Report Language: Chinese + English

## 1. Usage Overview

<table>
  <tr>
    <td><b>Tool/Model</b></td>
    <td><b>Version/Date</b></td>
    <td><b>Type</b></td>
    <td><b>Purpose</b></td>
    <td><b>Where Used (sections/files)</b></td>
  </tr>
  <tr>
    <td>OpenAI Codex (GPT-5)</td>
    <td>2026-02-02 (example)</td>
    <td>LLM / Generative AI</td>
    <td>Modeling rationale, derivation assistance, pseudo-code & project structure, debugging & visualization, paper fragments</td>
    <td>
      Q1/Q2/Q3 modeling protocol and design discussions;<br/>
      Q3 visualization & style: <code>MCM_Sim/26A/src/mcm26a/viz/q3_plots.py</code>;<br/>
      Q3 experiments & plotting scripts: <code>MCM_Sim/26A/src/scripts/run_q3_master_table_experiment.py</code>, <code>.../make_q3_master_table_plots.py</code>;<br/>
      paper materials: <code>MCM_Sim/26A/论文/理论模型/论文阶段/Q3材料/*/paper_fragment_en.md</code>
    </td>
  </tr>
  <tr>
    <td>GitHub Copilot (optional example)</td>
    <td>2026-01 (example)</td>
    <td>Code completion / boilerplate</td>
    <td>Boilerplate, type hints, test scaffolding suggestions</td>
    <td>Selected files under <code>MCM_Sim/26A/src</code> (to be filled by the team)</td>
  </tr>
  <tr>
    <td>Translation tool (optional example: DeepL/others)</td>
    <td>2026-01 (example)</td>
    <td>Translation</td>
    <td>CN→EN translation with terminology alignment and editing</td>
    <td><code>MCM_Sim/26A/论文/理论模型/论文阶段/Q3材料/00/paper_q3_en.md</code>, etc.</td>
  </tr>
</table>

## 2. Detailed Record for LLM / Generative AI

### 2.1 Tool / Model Information

- Tool/Model: OpenAI Codex (based on GPT-5)
- Version/Date: 2026-02-02 (example; replace with your real usage record)
- Usage Mode: local CLI (Codex CLI) with access to the project workspace
- Purposes in this project:
  1) standardize terminology and narrative (TTE, headroom margin, aging/SOH, usage fluctuations), producing paper-ready paragraphs;
  2) map the problem statement into implementable modules/experiments: sensitivity (PRCC/Tornado), assumption testing (ablation/structural comparison), uncertainty decomposition (total variance / observed anchoring);
  3) engineering support: script entry points, output-directory conventions, dual plotting modes (paper/study);
  4) debugging and verification: identify statistical/protocol pitfalls and provide reproducible fixes.

### 2.2 Interaction Logs (showcase examples)

> Disclaimer: The following Query/Output blocks are **summarized examples** to illustrate how AI was used in the workflow. Final models, parameters, results, and claims were independently verified by the team via reproducible code and experiments.

#### Log 1: From statement to implementable modeling protocol

- Time: 2026-01-30 10:20 (example)
- Query (summary):
  - convert Q1/Q2/Q3 requirements into an actionable task list;
  - define consistent outputs (TTE, risk metric, explainable decomposition);
  - propose a coherent section structure for the paper.
- Output (summary):
  - propose a unified framework centered on a continuous-time mechanistic model (ODE + cut-off events);
  - organize Q3 into three complementary tracks: parameter sensitivity, assumption sensitivity, usage-fluctuation sensitivity;
  - recommend a “Data-as-support” narrative: open datasets anchor scale and direction, not replace modeling.
- Verification notes:
  1) the team cross-checked each item against the original statement and removed off-scope content;  
  2) each metric was given a computable definition (especially undervoltage/headroom risk);  
  3) reproducibility constraints were enforced: every figure maps to a script entry and output path.

#### Log 2: Q3 sensitivity deliverables - an evidence chain of figures and experiments

- Time: 2026-01-31 09:40 (example)
- Query (summary):
  - which figures best answer “change assumptions/parameters/usage fluctuations -> how predictions change”?
  - what goes into main text vs appendix?
- Output (summary):
  - main-text candidates: PRCC heatmaps (mean TTE and headroom), mechanism ablation, seed-only distributions, total-variance decomposition, observed-anchored usage×aging decomposition;
  - appendix candidates: bootstrap confidence intervals, cross-cell robustness, compressed heatmaps as supporting evidence;
  - dual-mode plotting: paper figures are clean; study figures add definitions and reading guidance.
- Verification notes:
  - a unified evaluation protocol (units, thresholds, seed policy) was fixed and documented;
  - any visualization not directly answering the statement was removed.

#### Log 3: Debugging case - bootstrap CI protocol fix to avoid false “stability”

- Time: 2026-02-01 15:10 (example)
- Query (summary):
  - bootstrap CIs look too narrow; could the implementation be wrong?
  - how to preserve resampling multiplicity in a cluster bootstrap?
- Output (summary):
  - identify a common bug: boolean masks / dedup indexing collapses repeated draws, shrinking CIs;
  - propose a weighted cluster bootstrap: treat draw counts as weights and recompute decomposition fractions;
  - provide a verification checklist (weight distribution sanity check, seeded reproducibility, before/after comparison).
- Verification notes:
  - the team compared CI widths and stability before/after the fix;
  - corrected artifacts were stored as “v2” outputs to avoid overwriting prior results.

#### Log 4: Paper fragments and formula/LaTeX sanity checks

- Time: 2026-02-02 09:30 (example)
- Query (summary):
  - write bilingual (ZH/EN) paper paragraphs for the Q3-11a~e evidence set;
  - check LaTeX escapes (e.g., `\%`, subscripts).
- Output (summary):
  - provide a reusable “figure-to-claim” narrative template: define protocol -> interpret main effect -> interpret interaction -> add robustness evidence;
  - fix common LaTeX issues (escape `%`, avoid incorrect escaping that breaks math rendering).
- Verification notes:
  - the team aligned each sentence with computed variables and code outputs;
  - any statement implying external facts/citations without evidence was removed or rewritten.

## 3. Translation Tools (optional)

If the team used a dedicated translation tool (e.g., DeepL), it should be disclosed as follows (example wording):

- Tool: DeepL (or other)
- Version/Date: <TBD>
- Declaration:
  - full translation: translate the Chinese report into English and manually proofread terminology, grammar, and coherence;
  - partial translation: translate only selected sections while keeping formulas/symbols/figure captions unchanged.
- Proofreading: key terms, symbols, and units were manually verified.

## 4. Code Copilots / Auto-complete (optional)

- Tool: GitHub Copilot (or other)
- Version/Date: <TBD>
- Purpose: code completion and boilerplate suggestions during implementation
- Verification:
  1) all suggested code must pass minimal reproducible experiments and/or tests;  
  2) critical numerical steps (sampling, decomposition, threshold events) require manual review and comments;  
  3) variables without explicit definitions are not allowed into the final code base or paper.

## 5. Integrity, Verification, and Responsibility Statement

- We follow COMAP's disclosure policy by listing each AI tool, its purpose, and where it is used.
- AI outputs are not treated as final conclusions. All assumptions, parameter settings, experimental results, and claims are independently verified and reproducible via code.
- We mitigate known risks (hallucination, fabricated citations, concept drift, protocol mistakes) through controlled experiments, code review, and recomputation checks.

