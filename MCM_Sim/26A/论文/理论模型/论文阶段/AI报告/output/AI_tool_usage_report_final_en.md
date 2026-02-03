# Report on Use of AI Tools

## **OpenAI Codex (Feb 2, 2026 version, GPT-5-2)**

   **Query (exact wording)**:  
   Break the Problem A statement into an implementable task list for Q1/Q2/Q3, and specify the key outputs (e.g., TTE, undervoltage risk, sensitivity/uncertainty decomposition) and figures needed to build a clear evidence chain.

   **Output (complete output)**:  
   - Use a unified continuous-time mechanistic backbone: ODE-style SOC dynamics + a cut-off (termination) event; report TTE as the primary outcome and add at least one risk-facing metric.  
   - For Q1: build a coherent evidence chain (restatement → variables/parameters → scenario modeling → baseline prediction → order-of-magnitude checks against data/common sense).  
   - For Q2: identify the dominant drivers and use controlled one-at-a-time (OAT) contrasts to produce explainable conclusions and paper-ready figures.  
   - For Q3: structure the section into three parallel tracks—parameter sensitivity, assumption sensitivity, and usage-fluctuation sensitivity—and map each track to reproducible experiments and figures (e.g., PRCC/Tornado; ablation/structural comparisons; distributions/variance decomposition/observed anchoring).  

   **Query (exact wording)**:  
   Design a reproducible and clean project structure: script entry points, output directories, paper/study dual-mode plotting, and a “minimal main folder + archived other/” materials convention.

   **Output (complete output)**:  
   - Adopt a dual-mode plotting policy: paper figures are minimal and clean for the report; study figures include protocol definitions and reading guidance for internal auditing.  
   - Fix output directories and naming conventions; generate every figure/table via scripts to ensure traceability and reproducibility.  
   - Enforce a “paper materials” convention: each figure folder keeps only `figure.png` and `paper_fragment_zh.md`; all variants, data tables, English fragments, and notes go into `other/` to avoid overwriting and to preserve an audit trail.  

   **Query (exact wording)**:  
   The observed-anchoring “variance decomposition + bootstrap CI” looks overly stable. Check for statistical/implementation pitfalls and propose a reproducible fix without overwriting legacy artifacts.

   **Output (complete output)**:  
   - Flag a common pitfall: using boolean masks or deduplicated indexing during resampling can collapse repeated draws and artificially narrow confidence intervals.  
   - Use a weighted cluster bootstrap protocol: treat draw counts as weights when recomputing decomposition fractions; export a v2 result instead of overwriting prior artifacts.  
   - Preserve legacy outputs for manual comparison and traceability.  

## Verification and Responsibility Statement

- We verified AI-generated content for correctness and applicability and removed any unverifiable claims or implied citations.  
- Final models, parameters, and conclusions were independently developed and are reproducible; AI tools were used only as assistants.  

