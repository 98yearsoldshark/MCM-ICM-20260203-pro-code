# Battery Degradation Datasets (Two Types of Lithium-ion Batteries)

## Source / license (Mendeley Data)

This folder corresponds to **Data source B (battery degradation / aging)** described in:

- `MCM_Sim/26A/data/数据集/MCM2026_数据来源与说明文档.md`

Original dataset landing page / citation:

- Mendeley Data: `https://data.mendeley.com/datasets/v8k6bsr6tf/1` (mirror: `https://data.niaid.nih.gov/resources?id=mendeley_v8k6bsr6tf`)
- DOI: `10.17632/v8k6bsr6tf.1`
- License: **CC BY 4.0**

This folder contains two Excel workbooks that look like **pre-processed battery charging curves** sampled on a fixed **voltage grid**. They are suitable for battery degradation / SOH (state-of-health) / RUL (remaining useful life) modeling.

## What the data represents (interpreted)

For each `CellXX` sheet:

- **Rows (`Sample 1`, `Sample 2`, ...)**: sequential measurements for the same cell (most likely charge cycles, i.e., time order).
- **Columns (`2.5 V`, `3.0 V`, ...)**: voltage grid points.
- **Values (Ah)**: *cumulative charging capacity* at each voltage grid point during charging (a resampled/interpolated Q-V curve).

Practical notes:

- The **last voltage column** (e.g., `4.2 V` or `3.65 V`) can be treated as an **end-of-charge capacity proxy** for that sample.
- Since data is already on a fixed voltage grid, you can derive features such as `dQ/dV` (incremental capacity) or compare curve shape changes over time.

## Files

- `Dataset#3.xlsx`
  - Sheets: `Cell01`, `Cell02`, `Cell03`
  - Voltage grid: `3.0 V` .. `4.2 V` (step 0.01 V, 121 points)
  - End-of-charge capacity scale: ~2.7 Ah at early samples, ~1.7-1.8 Ah at late samples
  - Sample counts:
    - Cell01: 920
    - Cell02: 926
    - Cell03: 924

- `Dataset#5.xlsx`
  - Sheets: `Cell01`, `Cell02`, `Cell03`
  - Voltage grid: `2.5 V` .. `3.65 V` (step 0.01 V, 116 points)
  - End-of-charge capacity scale: ~28 Ah at early samples, ~21-22 Ah at late samples
  - Sample counts:
    - Cell01: 1420
    - Cell02: 1422
    - Cell03: 1420

## Excel layout details

Each sheet uses a 2-row header:

- Row 1: a description cell like `Cumulative charging capacity corresponding to the voltage grid (Ah)`
- Row 2: voltage column names (`3.0 V`, `3.01 V`, ...)
- Row 3+: sample data (`Sample n`)

## How to load (pandas)

```python
import pandas as pd

path = "Dataset#3.xlsx"          # or Dataset#5.xlsx
sheet = "Cell01"                 # Cell01/Cell02/Cell03

df = pd.read_excel(path, sheet_name=sheet, header=1)
df = df.rename(columns={df.columns[0]: "Sample"})

# Parse sample index as integer (optional)
df["SampleIndex"] = (
    df["Sample"].astype(str).str.extract(r"(\\d+)")[0].astype(int)
)
```

## Quick sanity checks (what you should verify)

Recommended checks before modeling:

- **Monotonicity vs voltage**: within each sample row, cumulative capacity should be non-decreasing as voltage increases.
- **Missing values**: there should be no NaN/empty entries.
- **Degradation trend**: the last-voltage capacity should generally decrease with `SampleIndex`.

Observed from a basic scan (no provenance info available):

- No missing values were found.
- Curves are almost perfectly monotonic; a small number of tiny negative steps may exist in `Dataset#3` (likely interpolation/rounding noise).
- End-of-charge capacity shows a strong decreasing trend across sample index (consistent with degradation).

## Caveats / provenance

These workbooks do **not** include detailed test protocol metadata such as:

- cell chemistry/manufacturer/model,
- temperature, C-rate, rest times,
- cutoff criteria, test equipment,
- whether samples correspond exactly to cycle counts.

Therefore, treat it as **competition/teaching data** or a **curated feature dataset**, not raw experimental logs. If you need scientific reproducibility, obtain the original source and test protocol.

## How this folder is used in MCM 2026 Problem A (battery side)

Per `MCM_Sim/26A/data/数据集/MCM2026_数据来源与说明文档.md` (Section 3.2), these workbooks are used to derive battery-aging states and OCV(SOC) parameters:

1) Load `Dataset#3.xlsx` and `Dataset#5.xlsx`, sheets `Cell01`~`Cell03`.
2) For each sample, treat the **highest-voltage column capacity** as full-charge capacity: `Q_full_Ah`.
3) For each cell, compute `SOH = Q_full_Ah / Q_full_Ah(sample 1)`.
4) Pick 6 representative aging labels per cell: `new (~1.00)`, `slight (~0.95)`, `moderate (~0.90)`, `aged (~0.85)`, `old (~0.80)`, `eol (min SOH)`.
5) For each representative sample, fit an OCV polynomial:
   - Define `SOC = Q(V) / Q_full_Ah`
   - Fit `V ≈ c0 + c1*SOC + ... + c5*SOC^5`
   - Output coefficients `ocv_c0` ~ `ocv_c5`

Derived outputs (already exported in this repo):

- Battery state table: `MCM_Sim/26A/data/数据集/MCM2026_battery_state_table.csv`
- Master modeling table (cartesian join with phone tests): `MCM_Sim/26A/data/数据集/MCM2026A题锂电池数据表：master_modeling_table.csv`

## Suggested use cases

- SOH estimation from Q-V / dQ/dV features
- Capacity fade modeling over cycles
- Remaining useful life (RUL) prediction
- Curve-shape similarity / drift detection

## License

CC BY 4.0 (per Mendeley Data landing page / DOI above).
