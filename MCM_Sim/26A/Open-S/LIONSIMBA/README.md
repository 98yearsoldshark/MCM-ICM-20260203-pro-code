# LIONSIMBA（本项目不采用）

本目录用于记录我们曾调研过的开源电池仿真工具 **LIONSIMBA**，以及在当前工作空间/项目约束下选择放弃使用它的原因。  
（最后更新：2026-01-30）

## LIONSIMBA 是什么

- LIONSIMBA（Lithium-ION SIMulation BAttery Toolbox）是一个以**有限体积法**为基础的锂离子电池电化学模型仿真工具箱，主要面向电池设计、仿真与**控制导向建模**。
- 主要实现语言为 **MATLAB/Octave**；典型工作流通过 `Parameters_init.m` 配置参数，通过 `startSimulation.m` 运行仿真。
- 官方仓库（参考）：`https://github.com/lionsimbatoolbox/LIONSIMBA`

## 为什么在本项目中放弃使用

- 当前工作空间不具备 MATLAB 支持；即便选择 Octave，仍需额外配置/编译相关依赖（例如 CasADi、SUNDIALS/IDA 接口等），集成成本较高。
- 本项目整体以 Python 为主，继续引入 MATLAB/Octave 生态会增加环境复杂度与可复现性成本。

## 替代方案（本项目采用）

- 见同级目录：`../PyBaMM/`  
  以 Python 生态为主，便于在本项目中集成、复现与二次开发。

## 状态

- 本目录仅用于保留调研记录，不包含可执行代码，也不参与项目运行流程。

