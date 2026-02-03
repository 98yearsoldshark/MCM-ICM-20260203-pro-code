# Report on Use of AI Tools (Showcase Version: OpenAI Codex / GPT-5)

> Note: This document is a **showcase example** for disclosure and formatting. It is allowed to be summarized and polished, and may not match the real chat history verbatim. Before submission, the team should replace placeholders (team number, exact dates, versions, and file paths) with the actual records and keep a reproducible evidence chain (scripts / outputs / parameters).

## Basic Information

- Contest: MCM/ICM 2026
- Team Number: <TBD>
- Selected Problem: Problem A
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
    <td>Statement-to-spec mapping, modeling protocol alignment, experiment design, project structure & debugging, visualization polishing, paper fragments</td>
    <td>
      Q1/Q2/Q3 modeling discussion & experiment planning;<br/>
      <code>MCM_Sim/26A/src/mcm26a/viz/q2_plots.py</code>, <code>q3_plots.py</code>;<br/>
      <code>MCM_Sim/26A/src/scripts/*.py</code>;<br/>
      <code>MCM_Sim/26A/论文/理论模型/论文阶段/Q2材料/*/paper_fragment_en.md</code>
    </td>
  </tr>
  <tr>
    <td>Translation tool (example: DeepL/others)</td>
    <td>2026-01 (example)</td>
    <td>Translation</td>
    <td>CN→EN paragraph translation and terminology alignment (no change to formulas/symbols)</td>
    <td>Chinese draft → English draft stage; specific files should be filled by the team</td>
  </tr>
  <tr>
    <td>Code completion tool (example: GitHub Copilot/others)</td>
    <td>2026-01 (example)</td>
    <td>Code completion</td>
    <td>Boilerplate, type hints, plotting scaffolds</td>
    <td>Selected files under <code>MCM_Sim/26A/src</code> (to be filled by the team)</td>
  </tr>
</table>

## 2. Detailed Record for LLM / Generative AI

### 2.1 Tool / Model Information

- Tool/Model: OpenAI Codex (based on GPT-5)
- Version/Date: 2026-02-02 (example; replace with your actual record)
- Usage Mode: local CLI (Codex CLI) with access to the project workspace
- Typical purposes in this project:
  1) translate statement requirements into “computable metrics + reproducible scripts + explainable evidence”;
  2) build a progressive validation path across model versions (Model-0/1/2/3…) and organize ablations;
  3) generate dual-mode figures: paper (clean) and study (with protocol definitions and reading guidance);
  4) identify and fix protocol mismatches (units, thresholds, statistics, seed strategy) that can bias results.

### 2.2 Interaction Logs (showcase examples)

> Disclaimer: The following logs are **summarized examples** intended to demonstrate the role of AI in the workflow. Final models, parameter choices, experiments, and claims were independently verified and made reproducible by the team.

#### Log 1: From statement to an actionable task list

- Time: 2026-01-30 10:20 (example)
- Query (summary)
  - parse Q1/Q2/Q3 scoring points and deliverables;
  - map text requirements into metrics (TTE, risk probability, drivers) and a figure list;
  - propose a paper narrative (main storyline + appendix evidence).
- Output (summary)
  - provide a “metric definition sheet” (every metric is computable in code);
  - propose a progressive model roadmap (quick Model-0 pass, then upgrade to Model-3 / anchoring / sensitivity decomposition);
  - define scripts and output directory conventions for reproducibility.
- Verification notes
  1) the team cross-checked items against the original statement and removed out-of-scope content;  
  2) a unified protocol was enforced (units, thresholds, terminology);  
  3) every figure must map back to: script + inputs + key parameters.

#### Log 2: Fixing the Q2 “condition impact” plot to avoid misinterpretation

- Time: 2026-02-01 15:40 (example)
- Query (summary)
  - the existing condition-variant plot has a confusing x-axis; how to redesign it in line with the statement?
  - how to replace “scenario-specific variant names” with a unified one-at-a-time (OAT) set of condition toggles?
- Output (summary)
  - implement a unified OAT condition set (high brightness / poor signal / cellular network / cold & hot contrasts) shared by all scenarios;
  - standardize the baseline to a constant room temperature (e.g., 20°C); treat temperature columns as directional contrasts to avoid mixing with UQ;
  - generate a single-source report so that figure.png and data.csv are derived from the same CSV table.
- Verification notes
  - the team cross-checked against Q2 text requirements and internal theory notes to ensure the plot directly answers “largest reductions / surprisingly little”;
  - “empty cells” are explicitly labeled as “not applicable (—)” to avoid being misread as a bug.

#### Log 3: Reproducibility and “do not delete old artifacts” policy

- Time: 2026-02-02 09:10 (example)
- Query (summary)
  - repeated plotting iterations overwrite outputs; how to prevent losing prior versions?
  - how to keep the paper-material directory clean while preserving auditability?
- Output (summary)
  - adopt a “paper directory keeps only final paper figure + Chinese fragment; everything else goes to other/” structure;
  - enforce “backup-before-overwrite” into other/_history/ for figures/data/fragments;
  - require about.md to record: source paths, generation scripts, key inputs and parameters.
- Verification notes
  - the team checked traceability (can we reconstruct how each artifact was produced?);
  - for major protocol changes, legacy figures are preserved for side-by-side review (not necessarily for the main text).

#### Log 4: Figure-to-claim writing template for paper fragments

- Time: 2026-02-02 10:00 (example)
- Query (summary)
  - write bilingual (ZH/EN) paragraphs that can be pasted into the paper for key figures;
  - ensure no unverifiable facts or external citations are introduced.
- Output (summary)
  - provide a reusable structure: define protocol → summarize key findings → explain mechanism (causal chain) → identify boundaries where the model performs well/poorly;
  - mark “explanatory notes (removable)” for easy team editing;
  - fix common formatting issues (e.g., LaTeX escapes, consistent figure references).
- Verification notes
  - each sentence is mapped to computable fields and can be re-derived from exported data tables;
  - any statement implying external facts without evidence is removed or rewritten into model-internal explanations + controlled comparisons.

## 3. Translation Tools (optional)

If a separate translation tool (e.g., DeepL) was used during final drafting, it can be disclosed as follows (example wording):

- Tool: DeepL (or others)
- Version/Date: <TBD>
- Declaration:
  - full translation: translate the Chinese report into English, then manually proofread terminology, grammar, and coherence;
  - partial translation: translate selected sections while keeping formulas/symbols/figure captions unchanged.
- Proofreading: key terms and units are manually verified; formulas and symbols remain unchanged.

## 4. Code Copilots / Auto-complete (optional)

- Tool: GitHub Copilot (or others)
- Version/Date: <TBD>
- Purpose: boilerplate and code completion during implementation
- Verification:
  1) suggested code must pass minimal reproducible experiments and/or tests;  
  2) critical numerical steps (sampling, statistics, threshold events) require manual review and comments;  
  3) undefined variables are not allowed into the final code base.

## 5. Integrity, Verification, and Responsibility Statement

- We follow COMAP’s disclosure policy by listing each AI tool, its purpose, and where it is used.
- AI outputs are not treated as final conclusions. All assumptions, parameter settings, experiments, and claims are independently verified and reproducible via code.
- We actively mitigate known risks (hallucination, fabricated citations, concept drift, statistical protocol mistakes) through controlled experiments, code review, and recomputation checks.

