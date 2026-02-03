# Q2 图像证据链（建议摆放顺序）

（这是讲解内容，论文中可删除）  
赛题 Q2 要求你：给出多 SOC0×多场景的 TTE，做不确定性，做 drivers，并用公开观测/合理行为做对照，说明模型哪里好/哪里差。  
建议在论文中按“先给结论图 → 再给解释图 → 再给对照图”的顺序铺陈：

1. **核心输出（必须）**
   - `01-Q2-TTE矩阵_场景×SOC0/figure.png`
   - `03-Q2-不确定性分布_UQ/figure.png`
   - `05-Q2-drivers矩阵_每种情形下驱动因素/figure.png`
   - `06-Q2-surprisingly_little_影响出乎意料地小/figure.png`

2. **解释差异（建议至少选 1~2 张）**
   - `13-Q2-解释性轨迹_待机/figure.png`
   - `14-Q2-解释性轨迹_游戏/figure.png`
   - `02-Q2-变体对比_条件变化对TTE影响/figure.png`
   - `04-Q2-不确定性宽度排名_模型好坏边界/figure.png`

3. **对照与验证（建议选 2~4 张）**
   - AndroWatts：`07-Q2-观测对照_AndroWatts总功耗/figure.png`
   - SmartphoneMeasurements（通信能耗）：`08-Q2-观测对照_通信单位能耗JMB/figure.png`
   - SmartphoneMeasurements（TTE 层面对齐）：`09-Q2-观测对照_TTE层面对齐/figure.png`
   - user_behavior（长时间/合理范围）：`10-Q2-观测对照_长时间TTE分布/figure.png`

4. **历史/老化（若你把 history 放进 Q2 或 Q4，可选 1~2 张）**
   - `11-Q2-历史老化影响_TTEvsSOH/figure.png`
   - `12-Q2-提前关机证据_终止SOCvsSOH/figure.png`
