<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.3 Fluctuations in Usage Patterns（Measured Trace Test） -->

## 7.3 Fluctuations in Usage Patterns: Measured Traces and a Controlled “Alpha Sweep”

To ensure our discussion of usage fluctuations is grounded in real data (as support, not a substitute for the mechanistic model), we used an open dataset of smartphone power measurements (Monsoon). For each measured power trace \(P(t)\), we constructed a family of equal-mean signals:
\[
P_{\alpha}(t)=\bar{P}+\alpha\cdot\big(P(t)-\bar{P}\big),\quad \alpha\in[0,1],
\]
where \(\alpha=0\) corresponds to the “mean-power approximation” and \(\alpha=1\) recovers the original fluctuation strength. We then simulated TTE for each \(\alpha\) and reported \(\Delta\)TTE(\%) relative to \(\alpha=0\).

![Figure Q3-10. Controlled fluctuation-strength sweep (alpha): ΔTTE(%) versus alpha, aggregated over measured traces.](../figure.png)

*Figure Q3-10* demonstrates a consistent trend: at fixed mean power, stronger fluctuations tend to reduce TTE (negative \(\Delta\)TTE), with rare but more extreme cases. This provides a causal, physically interpretable mechanism for “unpredictable drain”: bursty usage can push the battery into deeper voltage sag regimes (and closer to cut-off), which is not captured by a purely average-power view.
