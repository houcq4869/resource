# 研究综合（SYNTHESIS）

> 来源：ulw-research 会话 20261102-105649 的编排者综合分析（2026-11-02）· 对应主报告全部章节

---

# ULW-Research Synthesis — OpenHarmony 系统深度调研（海思适配视角）

Workers: 10 · Waves: 2 · Excursions: 0（未触发深度偏航） · Sources: ~200+ 观察（20+ 一手源域） · Verifications: git 协议仓库级实测为主 · Elapsed: ~2.5h

## Executive summary

OpenHarmony 是开放原子开源基金会孵化的开源 OS（Apache-2.0，华为 2020 捐赠起步），多内核（LiteOS-M/A + Linux LTS）、四层架构（内核/系统服务/框架/应用）、分布式软总线为底座的跨端协同设计。截至 2026-11-02：最新功能版本 7.0 Release（2026-08-22，API 26.0.0 SemVer 起点），当前 LTS 6.1（2026-07-31）；代码托管 2025-09-16 起整体迁至 GitCode（Gitee 停滞镜像）；无单体 monorepo（manifest 515 仓组装）；标准系统默认内核 linux-6.6（5.1.0 起）；HDF 为跨内核统一驱动框架；构建单引擎 build+hb。海思侧：Hi3516DV300 标准系统参考板 3.2 起弃用（小型保留至 7.0）、Hi3861 仍为轻量一等公民、**Hi3403V100/Hi3519AV200（hispark_aifly）为现行官方新主线**——5.1.0+Linux 6.6.86 官方套件、代码 2026-09-01 合入主线、6.1-LTS 免补丁直编，是「新海思 SoC 上 OpenHarmony」的完整模板。

## Findings by theme

1. **版本与治理**：W1/W9 双组收敛（docs release-notes 索引 + manifest tag + 镜像目录三源）；6.1.1-LTS（2026-10-31）为无 release note 的 cve-fix 维护标签。
2. **架构**：四层+四子系统集（官方名「系统基本能力/基础软件服务/增强软件服务/硬件服务」）；系统形态 RAM 基线三口径并存（开发 1MiB/认证 4MiB/团标分级）——已作为【冲突】标注。
3. **内核**：LiteOS-M（MCU+KAL CMSIS/POSIX）、LiteOS-A（仅 ARMv7-A）、Linux 4.19 维护/5.10/6.6 并存默认 6.6；板级补丁独立仓 kernel_linux_patches；HCK 插桩解耦为 6.x 新机制。
4. **子系统**：三套官方口径清单（29/44/57）；目录前缀=子系统集；映射五件套（subsystem_config+bundle.json+vendor config+inherit+manifest）。
5. **HDF**：跨内核驱动框架（khdf 三内核适配 + uhdf2 用户态）；HCS 自有 DSL 非 DT；平台驱动「模型注入」模式；Linux 侧适配器包装原生子系统并存；无 .drv 产物。
6. **构建**：单引擎结论（build.sh→build/hb/main.py）；build_lite 冻结；Python 3.11.4 内置、uv 非依赖；三级配置 device/soc+board+vendor；镜像按形态四套。
7. **应用与分布式**：ArkTS/ArkUI 声明式为正朔、Stage 模型现行；ArkCompiler 开源仓+IDE 不开源；HAP/HAR/HSP/APP；分布式栈五件套；同帐号设备互信认证等未开源（stub）。
8. **海思专题**：现状矩阵+三条移植指南+HiSpark 套件+生态动向；**Hi3403 模板**（wave-2）：双补丁机制（48 OH 源码 patch 仅 5.1 + SDK patch 含 ATF BL33）、编号内核补丁序列 0001-0010+幂等脚本、启动链 fip/uImage、治理「代码进主线/SIG 未毕业」、新 SoC 交付物六层清单。

## Contradictions（已标注进报告）

- 硬件基线三口径（开发/兼容规范/团标）；内核映射两口径（README 粗表 vs 细表）；LiteOS-A 虚拟内存布局两文档矛盾；Hi3863 上市状态（官网 vs 发布件）；hispark_aiflylite 文档有命令但公开仓无产品配置；DRM 默认值指南 vs config.json；appexecfwk 死配置（未终证）。

## Gaps（未闭合，均已记录）

- hispark_pegasus_3863 的构建入口（CI job 定义/包内 config）；P7885 主线目录对标细节；TF-A 补丁是否上游化；「PMC 2026-05」存证；ArkCompiler AOT PIC；appexecfwk 残留终证。

## Expansion trace

Wave 1（9 workers）→ ~40 LEADs：3 条双源闭合（版本/GitCode/默认内核）、1 条进 Wave 2（Hi3403 模板）、其余 deferred 记录。Wave 2（1 worker）→ 6 LEADs 全部 deferred（不影响核心交付）。收敛规则：2 波完成、无新的可行动线索。
