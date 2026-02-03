# Report on Use of AI Tools (Demo: Codex / GPT-5)

> Note: This is a “showcase” example. Some descriptions may be summarized and polished and may not match the conversation verbatim. Before submission, please replace placeholders (team number, dates, tool versions) with your actual records and remove any non-applicable optional items.

## Basic Information

- Contest Name: MCM/ICM 2026 (Simulated set: MCM_Sim/26A)
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
    <td><b>Usage Location (Section/File)</b></td>
  </tr>
  <tr>
    <td>OpenAI Codex (GPT-5)</td>
    <td>2026-02-02</td>
    <td>Large Language Model (LLM) / Generative AI</td>
    <td>
      Interpreting requirements and fixing modeling “definitions”; designing a continuous-time SOC(t) model;
      engineering scripts/output structure; producing paper/study visualization pairs;
      using open data as order-of-magnitude support (not a substitute); drafting figure captions and paper fragments
    </td>
    <td>
      Q1 (Continuous-time model + open-data support figures):<br/>
      <code>MCM_Sim/26A/src/scripts/make_q1_tte_boxplot_models_vs_opendata_soft.py</code>;<br/>
      <code>MCM_Sim/26A/src/scripts/make_q1_tte_radar_with_opendata_support_soft.py</code>;<br/>
      <code>MCM_Sim/26A/src/scripts/tune_q1_opendata_mapping_to_model.py</code>;<br/>
      <code>MCM_Sim/26A/src/scripts/replot_q1_tte_boxplot_models_variants.py</code>;<br/>
      Scenario config: <code>MCM_Sim/26A/src/configs/scenarios_q1_v1_5cases.json</code>;<br/>
      Open dataset: <code>MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv</code>;<br/>
      Paper materials: <code>MCM_Sim/26A/论文/理论模型/论文阶段/Q1材料/06-模型0vs模型1_TTE对比/</code>
    </td>
  </tr>
  <tr>
    <td>Translation tool (optional example: DeepL/others)</td>
    <td>&lt;YYYY-MM-DD&gt;</td>
    <td>Translation</td>
    <td>CN→EN translation and terminology harmonization (for final English draft)</td>
    <td>Entire report / selected sections (to be filled before submission)</td>
  </tr>
  <tr>
    <td>Code copilot (optional example: GitHub Copilot/others)</td>
    <td>&lt;YYYY-MM-DD&gt;</td>
    <td>Auto-completion / boilerplate suggestions</td>
    <td>Implementation acceleration only (not a source of modeling conclusions)</td>
    <td>Selected files under <code>MCM_Sim/26A/src</code> (to be filled before submission)</td>
  </tr>
</table>

## 2. Detailed Records of LLM / Generative AI (Codex / GPT-5)

### 2.1 Tool/Model Information

- Tool/Model: OpenAI Codex (GPT-5)
- Version/Date: 2026-02-02 (demo; replace with your actual usage record)
- Usage Method: Local CLI (Codex CLI) with access to the project workspace
- Purposes (focused on Q1 “continuous-time model + data-as-support”):
  1) Convert the problem statement into implementable continuous-time equations and event definitions (SOC ODE + cut-off event + TTE definition);
  2) Formalize five scenarios (S1–S5) and design an interpretable “gate + priority” mapping using device-state features;
  3) Build an evidence chain where open data constrains plausible magnitudes and coverage bounds, rather than replacing the mechanistic model;
  4) Engineering and reproducibility: consistent units (seconds internally, hours for TTE plots), paper/study plot modes, output paths, and plot versioning.

### 2.2 Interaction Log (Showcase Examples)

> Note: The following “Query/Output” items are summarized examples for disclosure. Final models, parameters, and conclusions were verified by the team and are reproducible via code.

#### Log 1: From Q1 text to an executable continuous-time model definition

- Time: 2026-01-30 10:20 (example)
- Query (summary):
  - How to model SOC(t) with a continuous-time equation (or system) and define TTE?
  - What does “data as support, not substitute” mean operationally?
- Output (summary):
  - Proposed an ODE backbone: <code>dSOC/dt = -I(t)/Q_eff</code>, and defined TTE as the first hitting time to cut-off voltage / termination event;
  - Suggested a modular load-power decomposition (screen, CPU/GPU, network, GPS, background) that drives I(t);
  - Emphasized that pure discrete curve fitting / timestep regression is not acceptable as a replacement for the mechanistic model.
- Verification & revision notes:
  1) Cross-checked every definition against the problem statement;  
  2) Fixed unit conventions (seconds internally; hours only for presentation);  
  3) Wrote the key definitions into configs and figure notes for reproducibility.

#### Log 2: Using AndroWatts open data as “order-of-magnitude support” with transparent limits

- Time: 2026-01-31 14:05 (example)
- Query (summary):
  - The dataset <code>aggregated.csv</code> has no scenario labels. How to derive a scientific, interpretable, and reproducible mapping to S1–S5?
  - How to present open data in the paper without implying it replaces the mechanistic model?
- Output (summary):
  - Designed a “gate + priority” mapping based on device states (CPU/GPU frequency, brightness/color, network activity, etc.);
  - Provided a hard mapping (deterministic) and a soft mapping (probabilistic weighting) to enable robustness comparisons;
  - Added an explicit coverage-bound note: if the minimum power in open data is not low enough, the S1 (deep standby) TTE becomes a lower bound rather than a full-range estimate.
- Verification & revision notes:
  1) Kept data provenance and license as referenced from the dataset’s metadata/README;  
  2) Fixed mapping rules/thresholds in scripts/configs (no “hand-waving”);  
  3) Marked “lower bound” clearly on the plot to avoid misinterpretation.

#### Log 3: High-value Q1 figures — radar (log-radius polygon) + overlaid boxplots

- Time: 2026-02-01 11:20 (example)
- Query (summary):
  - Replace the five-scenario bar chart with a pentagon radar chart, with log-radius ticks (2/4/8/16/32 h);
  - Overlay open-data TTE distributions with Model-0/Model-1 predictions in a single, paper-ready visualization.
- Output (summary):
  - Radar chart: polygon (pentagon) grid + log-radius ticks + clear palette; exported both paper and study versions;
  - Boxplots: open data shown as large boxplots; Model-0/Model-1 shown as small boxplots (from model sampling/UQ-lite), plus two types of annotations:
    - Median relative bias (M0 vs Open, M1 vs Open);
    - Coverage counts (n_eff(open), n(model)).
- Verification & revision notes:
  - All figures are script-generated (reproducible), with a paper/study pair to balance readability and transparency.

#### Log 4: Layout tuning without overwriting historical plots

- Time: 2026-02-02 09:10 (example)
- Query (summary):
  - Batch-generate “flatter/tighter” layout variants (x-gap, figure width, y-tick padding, legend position) for manual selection;
  - Keep an audit trail (no overwriting old plots).
- Output (summary):
  - Implemented a replot-only script that reads the same statistics CSVs and outputs multiple layout variants with parameterized filenames;
  - Archived previous outputs into an <code>archived/</code> folder for traceability.
- Verification & revision notes:
  - The team selects final layouts based on parameterized filenames; every paper figure has a study counterpart for internal checking.

## 3. Translation Tools (Optional)

- Tool: DeepL (or others)
- Version/Date: <TBD>
- Usage statement (example):
  - Full-text translation: translate Chinese draft into English, followed by manual terminology alignment and proofreading;
  - Partial translation: only translate selected sections while keeping formulas/symbols/figure titles unchanged.
- Proofreading notes: terminology, symbols/units, and figure references are manually verified by the team.

## 4. Code Copilots / Auto-complete (Optional)

- Tool: GitHub Copilot (or others)
- Version/Date: <TBD>
- Purpose: auto-completion and boilerplate suggestions during implementation
- Verification notes (example):
  1) Any suggested code must pass minimal reproducible experiments;  
  2) Critical numerical steps (sampling, statistical definitions, termination events) are reviewed and documented;  
  3) Variables without explicit definitions/units are not allowed to enter the final code/paper conclusions.

## 5. Integrity, Verification, and Responsibility Statement

- We follow COMAP’s AI disclosure policy by stating the AI tools used, their purposes, and where they were applied.
- We do not treat AI outputs as final conclusions. All model assumptions, parameter choices, experiment results, and conclusions were independently verified by the team and are reproducible.
- We actively guard against typical AI risks (hallucinations, fabricated citations, conceptual drift, statistical definition bugs) via controlled experiments, code review, recomputation, and versioned figure generation.

