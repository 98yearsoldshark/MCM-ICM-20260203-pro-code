# Report on Use of AI Tools

## Basic Information

- Contest: Mathematical Contest in Modeling / Interdisciplinary Contest in Modeling (MCM/ICM) 2026
- Team Number: <TBD>
- Selected Problem: Problem A
- Report Language: English (final submission) + Chinese (working notes/comments)

## 1. Usage Overview

<table>
  <tr>
    <td><b>Tool/Model</b></td>
    <td><b>Version/Date</b></td>
    <td><b>Type</b></td>
    <td><b>Purpose</b></td>
    <td><b>Where Used (Section/File)</b></td>
  </tr>
  <tr>
    <td>OpenAI Codex (GPT-5)</td>
    <td>2026-02-02 (example; replace with the team's record)</td>
    <td>Large Language Model (LLM) / Generative AI</td>
    <td>
      Requirements interpretation and terminology alignment; modeling-structure/derivation assistance; experiment design (controls/ablations);
      engineering scripts and output conventions; visualization (paper/study dual modes) and layout tuning;
      drafting paper fragments (captions/context) and consistency checks
    </td>
    <td>
      Code base: <code>MCM_Sim/26A/src</code> (scripts, viz, configs, etc.);<br/>
      Paper materials: <code>MCM_Sim/26A/论文/理论模型/论文阶段/Q1材料</code>, <code>Q2材料</code>, <code>Q3材料</code>;<br/>
      Q3 example: <code>MCM_Sim/26A/src/scripts/run_q3_master_table_experiment.py</code>,
      <code>.../make_q3_master_table_plots.py</code>, <code>MCM_Sim/26A/src/mcm26a/viz/q3_plots.py</code>
    </td>
  </tr>
  <tr>
    <td>Translation tool (if used: DeepL/others)</td>
    <td>&lt;YYYY-MM-DD&gt;</td>
    <td>Translation</td>
    <td>CN→EN translation and terminology harmonization (no changes to formulas/symbols)</td>
    <td>Entire report / selected sections (to be filled before submission)</td>
  </tr>
  <tr>
    <td>Code copilot (if used: GitHub Copilot/others)</td>
    <td>&lt;YYYY-MM-DD&gt;</td>
    <td>Code completion</td>
    <td>Boilerplate and auto-completion (implementation acceleration only; not a source of conclusions)</td>
    <td>Selected files under <code>MCM_Sim/26A/src</code> (to be filled before submission)</td>
  </tr>
</table>

## 2. Detailed Record for LLM / Generative AI (Codex / GPT-5)

### 2.1 Tool/Model Information

- Tool/Model: OpenAI Codex (based on GPT-5)
- Version/Date: 2026-02-02 (example; replace with the team's record)
- Usage Method: Local CLI (Codex CLI) with access to the project workspace
- Purposes (aligned with the workflow required by the statement):
  1) translate statement requirements into computable metrics and reproducible experiments (e.g., TTE, headroom margin, sensitivity/ablation/uncertainty decomposition);
  2) structure a progressive roadmap across model versions (Model-0/1/2/3…) and define validation/control sets for each stage;
  3) produce paper/study figure pairs: paper for the submission (clean), study for internal auditing (with protocols and reading notes);
  4) identify and fix protocol mismatches (units, threshold events, sampling/statistics, random-seed policies, plot annotations) that may bias results.

### 2.2 Interaction Log (summary disclosure)

> Note: The logs below are summarized for disclosure. Final models, parameters, experiments, and claims were independently verified by the team and are reproducible.

#### Log 1: Q1 (continuous-time SOC/TTE) — from text to implementable definitions

- Time: <YYYY-MM-DD HH:MM>
- Query (summary):
  - how to define SOC(t) and TTE (time-to-empty) in a continuous-time setting?
  - how to operationalize “data as support, not substitute” in the paper?
- Output (summary):
  - proposed an ODE + event backbone (TTE as the first hitting time to cut-off voltage / termination event);
  - decomposed load power into interpretable modules (screen, CPU/GPU, network, GPS, background) and scenario switching;
  - explicitly avoided “pure regression/curve fitting as a substitute for mechanistic modeling.”
- Verification notes:
  1) cross-checked definitions against the statement and removed off-scope items;  
  2) fixed unit conventions (seconds internally; hours only for presentation);  
  3) wrote key definitions into configs/scripts and figure notes for reproducibility.

#### Log 2: Q1 (open-data support) — scenario mapping and coverage bounds

- Time: <YYYY-MM-DD HH:MM>
- Query (summary):
  - when open datasets have no “scenario labels,” how to build an interpretable and reproducible mapping and document coverage limits?
- Output (summary):
  - designed a gate + priority mapping (hard mapping vs soft weighting) to map observed samples into S1–S5;
  - documented coverage boundaries (e.g., extreme conditions may be missing; some estimates become lower bounds).
- Verification notes:
  - thresholds, priorities, and exported statistics are fixed in scripts and can be re-derived from data tables.

#### Log 3: Q2 (condition impact) — unified one-at-a-time (OAT) contrasts to avoid misreading

- Time: <YYYY-MM-DD HH:MM>
- Query (summary):
  - existing “condition comparison” plots mix axes/protocols; how to redesign into a reviewer-friendly OAT toggle set?
- Output (summary):
  - proposed a unified OAT set (e.g., high brightness / poor signal / cellular / cold & hot contrasts) shared across scenarios;
  - standardized the baseline so that each condition column is a clean directional contrast (not mixed with uncertainty propagation).
- Verification notes:
  - cross-checked against the Q2 wording (largest reductions / surprisingly little) to ensure direct alignment.

#### Log 4: Q3 (observed anchoring + uncertainty) — variance decomposition and bootstrap CI protocol fix

- Time: <YYYY-MM-DD HH:MM>
- Query (summary):
  - are decomposition/CI results “too stable” due to implementation details?
  - how to preserve multiplicity in cluster bootstrap resampling?
- Output (summary):
  - identified a common pitfall: boolean masks / dedup indexing collapses repeated draws, shrinking CIs;
  - replaced with a weighted cluster bootstrap (use draw counts as weights) and exported v2 artifacts to avoid overwriting older results.
- Verification notes:
  - compared CI width and stability before/after the fix; preserved legacy plots for manual review.

#### Log 5: Paper fragments and layout audits — consistent “figure-to-claim” writing

- Time: <YYYY-MM-DD HH:MM>
- Query (summary):
  - draft bilingual paragraphs for key figures and ensure LaTeX/notation consistency (e.g., `\%`, subscripts);
  - keep old figure versions for auditability while iterating on layout.
- Output (summary):
  - provided a reusable narrative template: define protocol → summarize findings → mechanism explanation → boundaries/limitations;
  - fixed formatting issues (LaTeX escaping, consistent figure references) and enforced versioned outputs.
- Verification notes:
  - mapped each claim to exported tables and reproducible scripts.

## 3. Translation Tools (if used)

- Tool: DeepL (or others)
- Version/Date: <TBD>
- Usage statement:
  - full translation: translate the Chinese draft into English, then manually proofread terminology, grammar, and coherence;
  - partial translation: translate selected sections while keeping formulas/symbols/figure titles unchanged.
- Proofreading: terminology, units, symbols, and figure references are manually verified.

## 4. Code Copilots / Auto-complete (if used)

- Tool: GitHub Copilot (or others)
- Version/Date: <TBD>
- Purpose: auto-completion and boilerplate suggestions during implementation
- Verification:
  1) suggested code must pass minimal reproducible experiments/tests;  
  2) critical numerical steps (sampling, statistical definitions, termination events) are manually reviewed and documented;  
  3) variables without explicit definitions (including units) are not allowed into the final code/paper conclusions.

## 5. Integrity, Verification, and Responsibility Statement

- We follow COMAP’s AI disclosure policy by listing AI tools used, their purposes, and where they were applied.
- AI outputs are not treated as final conclusions. All assumptions, parameters, experiments, and claims are independently verified and reproducible via code.
- We mitigate typical risks (hallucinations, fabricated citations, concept drift, protocol mistakes) through controlled comparisons, code review, recomputation checks, and versioned artifacts.

