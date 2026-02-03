# Report on Use of AI Tools

# Basic Information

Contest Name: Mathematical Contest in Modeling/Interdisciplinary Contest inModeling (MCM/ICM) <Year>

• Team Number: <xxxxxx>

• Selected Problem: <A/B/C/D/E/F>

• Report Language: <English / Chinese $^ +$ English, etc.>

# 1. Usage Overview

<table><tr><td>Tool/Model</td><td>Version/Date</td><td>Type</td><td>Purpose</td><td>Usage Location (Section/File)</td></tr><tr><td>OpenAI ChatGPT (GPT-5)</td><td>&lt;YYYY-MM-DD&gt;</td><td>Large Language Model (LLM)/Generative AI</td><td>Outline structuring / Polishing / Pseudo-code</td><td>&lt;Sec 2.1; Appendix A&gt;</td></tr><tr><td>DeepL</td><td>&lt;YYYY-MM-DD&gt;</td><td>Translation Tool</td><td>Full-text translation (Chinese → English)</td><td>Entire report</td></tr><tr><td>GitHub Copilot</td><td>&lt;YYYY-MM-DD&gt;</td><td>Code Copilot</td><td>Auto-completion / Boilerplate code</td><td>&lt;simulation.py&gt;</td></tr></table>

# 2. Detailed Records of LLM / Generative AI

# 2.1 Tool/Model Information

• Tool/Model：OpenAI ChatGPT

• Version/Date $^ +$ Model Name: <<e.g., Nov 5, 2023 version, ChatGPT-4>

• Usage Method (Optional): <Web / App / API (Application Programming Interface)>

• Purpose: ${ \tt < } { \tt < e . g . }$ ., Generating structural ideas, polishing expressions, creating pseudo-code frameworks>

• Where Used: <<e.g., Sec. 2; Sec. 4; Appendix Code>

# 2.2 Interaction Log

# Log #1

• Time: <YYYY-MM-DD HH:MM>

Query

We are practicing for the "2016 MCM Problem B: Space Junk". Please provide 3 possiblemodeling ideas. For each idea, include: key assumptions, main variables, and core indicators(to evaluate the quality of the solution). Do not fabricate data or citations. Please output in astructured outline.

# • Output

Idea 1: Orbital Debris Quantity Dynamics (Stratified/Segmented Population Model)

Assumptions: Classify debris by size; collisions generate new debris; debris removalstrategies affect the reduction rate of specific classes.

Variables: Quantity of debris in each class, N_i(t); collision rate function; removal rate, r_i(t).

Indicators: Collision risk, stabilization time, cost.

Idea 2: Optimization Model for Intervention Combinations

Decision Variables: Annual removal quantity (by orbit type); budget allocation.

Objective: Minimize the sum of risk-weighted values and costs; Constraints: Budget limits,feasibility.

Idea 3: Agent-Based Simulation

Simulate each target using orbital parameters; events include launch, orbital decay, collision,and removal.

Indicators: Debris growth trend, sensitivity to strategy parameters.

# • Verification and Revision Notes:

1. We verified: Whether there were unsubstantiated claims/fabricated citations; whether keyvariables were clearly defined; whether they were consistent with our data/assumptions.

2. We revised: Removed inapplicable assumptions; replaced "verbal descriptions" with ourown derivation and simulation results.

3. Final Usage: Only referenced the structure; the final model, parameters, and conclusions

were independently developed by the team and are reproducible.

# Log #2

• Time: <YYYY-MM-DD HH:MM>

• Query

Please polish the following English paragraph into clearer and more concise academicexpression. Keep the technical meaning unchanged and do not add new facts.

[Paste our original paragraph here]

# • Output

We model the water temperature as a balance between heat input from the faucet and heat lossto the environment.

Assuming the water is well-mixed, the temperature evolves according to ...

# • Verification and Revision Notes:

1. We cross-checked each sentence: Whether new conclusions/data were introduced;whether terminology was consistent; whether formulas and symbols remainedunchanged.

2. Rewrote expressions that were inconsistent with our derivations, and prioritized our ownderivations.

# 3. Translation Tools

• Tool：DeepL

• Version/Date：<YYYY-MM-DD>

• Usage Statement:

o Full-text Translation: Used DeepL to translate the entire Chinese report intoEnglish. The team manually proofread terminology, grammar, and logicalcoherence.

o Proofreading Notes: We manually proofread terminology, grammar, andlogical coherence; formulas and symbols remained unchanged.

• Proofreading Notes: We manually proofread terminology, grammar, and logicalcoherence; formulas and symbols remained unchanged.

# 4. Code Copilots / Auto-complete / AI Features in Mathematical Software

• Tool：GitHub Copilot

• Version/Date：<YYYY-MM-DD>

• Purpose: Provide auto-completion and boilerplate code suggestions for implementingsimulation/optimization code.

• Usage Location: <<e.g., simulation.py; optimizer.ipynb>

• Verification Notes:

o All code suggested by GitHub Copilot was reviewed, tested, and modified (ifnecessary) by the team before being included in the final results.

# 5. Integrity, Verification, and Responsibility Statement

We have verified the accuracy, validity, and appropriateness of AI-generated contentand its citations, and corrected any errors or inconsistencies found.

• We have noted and avoided potential plagiarism risks; traced and verified text andcitations that may come from external sources, and made necessary rewrites orcitation annotations.