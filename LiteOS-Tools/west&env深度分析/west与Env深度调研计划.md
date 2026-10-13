# west 与 Env 深度调研计划（LiteOS L0/L1 构建工具预研）

> 定稿日期：2026-10-08
> 基准文档：《汇报最终版.md》
> 目标读者：后续执行本调研的成员（含 AI 会话）

---

## 〇、背景与定位

### 0.1 从基准文档出发的问题清单

《汇报最终版.md》已明确 LiteOS 的工具短板与建设方向，本次调研直接服务其中三条：

| 基准文档结论                                          | 与本调研的关系                                        |
| ----------------------------------------------- | ---------------------------------------------- |
| 开发环境：❌ 只能 Linux 开发；改进方向 = Windows 一键安装包 + 最小源码集 | Env 的"自带工具链免装包"与 west 的 `west sdk` 分发机制是两个现成参考 |
| 编译构建：✅ 组件化强，但环境重（70GB）、强依赖 Linux                | west 的 manifest 多仓管理是"最小源码集"的机制参考              |
| 烧录下载：❌ 无命令行烧录                                   | `west flash` 的 runner 抽象是此前已锁定的对标方向            |
| 竞争力方向一：一条命令生成 Keil/IAR/VS Code 原生工程             | RT-Thread `scons --target=xxx` 导出器是唯一已验证的同类实现  |
| 竞争力方向三：双构建后端（GN 主线 + CMake 轻量兜底）                | west 本身就是"壳与后端分离"的架构样本（west 不含构建逻辑，只封装 CMake）  |

**结论**：LiteOS L0（LiteOS-M 轻量系统）/ L1（LiteOS-A 小型系统）的构建工具建设**主要参考 west**，Env 作为"Windows 免装 + IDE 工程导出"两个专题的补充参考。

### 0.2 现有调研的缺口

《五大RTOS工具逐个详解.md》对 west/Env 的记录停留在**命令清单 + 能力描述**层：

- west：只列了 `west init/update/build/flash/debug/sign/boards` 等命令名，未回答"怎么实现的"；
- Env：只写了"menuconfig + pkgs + scons + 自带工具链"，未拆解内部结构。

**本计划补"实现机制"层**：源码架构、关键数据流、扩展点、可移植性评估，最终产出"LiteOS 可借鉴什么、怎么借鉴、不借鉴什么"。

### 0.3 范围边界（明确不做的事）

- ❌ **Twister 不深研**：此前已核实其深绑 west/CMake/board YAML，不可复用（见《各OS工具链现状一页总结》）；
- ❌ **RT-Thread Studio 不深研**：专有许可 + Eclipse 基座 + 仅 Windows，机制不可复制，只作结论引用；
- ❌ **west 的 CMakeLists 工程细节不深研**：LiteOS 主线是 GN，Zephyr 的 CMake 工程文件本身不迁移；要迁移的是 **west 的"壳"机制（CLI 入口、扩展注册、runner 抽象、manifest）**；
- ✅ 聚焦两个工具的**命令行工具层**：安装分发、命令体系、构建封装、烧录/调试抽象、IDE 工程导出、Windows 支持。

---

## 一、调研对象

| 对象                         | 仓库                                    | 初判重点路径（以实际版本为准，读码时修正）                                                                                                                      |
| -------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| west 工具本体                  | zephyr 主仓 `scripts/west/`             | `app/`（CLI 入口与引导）、`commands.py`（命令注册）、`manifest/`（west.yml 解析）、`build/`（CMake 封装）、`config.py`（三层配置）                                        |
| Zephyr 内置 west 子命令         | zephyr 主仓 `scripts/west_commands/`    | `build.py`、`flash_debug.py`、`runners/`（`core.py` 的 `ZephyrBinaryRunner` + openocd/jlink/pyocd/nrfjprog 等后端）、`boards.py`、`sign.py`、`sdk.py` |
| west 命令注册清单                | zephyr 主仓 `scripts/west-commands.yml` | 扩展机制的声明格式                                                                                                                                  |
| RT-Thread Env（Linux/macOS） | `RT-Thread/env`                       | 仓库结构、`env.sh` 引导、命令封装                                                                                                                      |
| RT-Thread Env（Windows）     | `RT-Thread/env-windows`               | 自带工具链的打包方式、`env.cmd` 引导、免装机制                                                                                                               |
| RT-Thread 构建系统             | `RT-Thread/rt-thread` 的 `tools/`      | `building.py`（构建核心 + `tgt_dict`）、`options.py`、`targets/*.py`（约 20 个 IDE 导出器）、BSP 内 `SConstruct`/`template.uvprojx` 等模板                     |

**版本策略**：读码前先锁版本（zephyr 取当前 LTS 主线 tag；rt-thread 取 master + 最新 release tag 各一份），所有产出标注"基于 vX.Y.Z"。

---

## 二、核心研究问题（调研必须回答的问题清单）

### 2.1 west 篇（9 问，重点）

| # | 问题 | 为什么重要（映射 LiteOS） |
|---|---|---|
| W1 | **分层架构**：west 如何把"多仓管理（init/update）"与"构建/烧录（build/flash）"解耦在一个 pip 包里？bootstrap 与 commands 的边界在哪？ | LiteOS 工具的总体架构分层依据 |
| W2 | **manifest 多仓管理**：`west.yml` 的 schema（projects/import/fork/allowlist/blocklist）如何设计？`west init/update` 的 git 操作与 revision 解析怎么做？`.west/` topdir 发现机制？ | "最小源码集 + 70GB 减重"的机制参考 |
| W3 | **扩展机制**：`west-commands.yml` 如何把 Zephyr 自己的命令（乃至 MCUboot、nRF Connect SDK 的命令）注册进 west？第三方仓如何加命令而不改 west 本体？ | **LiteOS 加自家命令（`liteos build/flash/export`…）的官方姿势**，双构建后端可插拔的基础 |
| W4 | **构建封装**：`west build` 如何包装 CMake + Ninja？参数透传、build 目录约定（`build/`、`CMAKE_EXPORT_COMPILE_COMMANDS`）、sysbuild 多镜像组织方式？ | 参考"壳不碰构建逻辑"的封装边界 |
| W5 | **runner 烧录/调试抽象**：`ZephyrBinaryRunner` 基类契约是什么？runner 的解析优先级（命令行 > 板级配置 > 构建产物 > 默认）？`west flash --dry-run` 如何实现？支持哪些后端、新增一个后端要写多少代码？ | **CLI 烧录短板的直接对标**（此前方向 #6 已锁定 runner 四后端） |
| W6 | **工具链分发**：`west sdk`（sdk-ng）的 manifest 与多架构布局？Windows 原生安装链路（winget 依赖 + SDK 下载）？ | Windows 一键安装包的机制参考 |
| W7 | **配置系统**：`west config` 模仿 git config 的三层配置（system/global/local）如何实现？ | 轻量、够用的工具自身配置方案 |
| W8 | **boards 发现**：`west boards` 如何扫描板卡目录？board.yml / HWMv2 硬件模型如何支撑检索？ | 补"官方芯片总表"选型入口的参考 |
| W9 | **Windows 原生**：west 自身在 Windows 上跑通的依赖集合是什么？哪些环节官方标注 Windows 可用/不可用？ | 校验 LiteOS "Windows 原生 30 分钟点灯"可行性 |

### 2.2 Env 篇（7 问）

| # | 问题 | 为什么重要（映射 LiteOS） |
|---|---|---|
| E1 | **env / env-windows 仓库内容盘点**：到底打包了哪些东西（Python/SCons/GCC/QEMU/dtc 的具体版本与体积）？`env.sh` / `env.cmd` 引导时做了什么（PATH 注入？环境变量？）？ | Windows 一键安装包的"第一手抄作业对象" |
| E2 | **menuconfig 实现**：Kconfig 前端用的什么（kconfig-frontends / kconfiglib）？`.config` → `rtconfig.h` 的生成流程？与内核 Kconfig 源的组织方式？ | LiteOS 已用 Kconfig，重点看前端集成方式 |
| E3 | **pkgs 包管理**：包索引的数据格式？包的 Kconfig 如何并入全局 menuconfig？`pkgs --update` 的下载与版本管理（git clone？版本号策略）？ | LiteOS 组件仓库的分发参考 |
| E4 | **SCons 构建核心**：`SConstruct`（BSP 层）→ `building.py`（框架层）→ 组件 `SConscript` 的三层结构？组件如何用 `DefineGroup` 注册源文件与宏？配置变化如何驱动构建内容变化？ | 理解"单一真源"如何维持 20 种导出目标不漂移 |
| E5 | **`--target` IDE 工程导出器**（**Env 篇最重点**）：`tools/targets/*.py` 每个导出器的实现模式——是模板文件替换还是程序化生成 XML？BSP 内模板文件（如 `template.uvprojx`）扮演什么角色？配置变更后"工程再生"的机制与用户体验？ | **竞争力方向一（一条命令导出 Keil/IAR/VS Code 工程）的唯一成熟参考实现** |
| E6 | **Windows 免装机制**：env-windows 如何做到免装 Python/SCons？内嵌 Python 发行版的坑（控制台编码、路径空格等）如何处理？ | 直接复用的工程经验 |
| E7 | **版本兼容策略**：env v2.0 仅完整支持 RT-Thread > v5.1.0、旧内核需 v1.5.x——这种约束靠什么机制实现与声明？ | LiteOS 工具与多版本内核的兼容设计参考 |

### 2.3 汇总篇（对比与映射，1 问）

**C1**：west 与 Env 的机制级对比（入口命令体系 / 多仓与包管理 / 配置系统 / 构建封装方式 / 工具链分发 / IDE 导出 / 烧录调试抽象 / 扩展机制 / Windows 支持 / 许可），并逐项给出"LiteOS L0/L1 是否借鉴、怎么借鉴"的结论。

---

## 三、调研方法

1. **源码为准（一手原则）**：三个仓库 clone 到本地，锁定版本后逐模块读码；所有结论必须带证据（文件路径 + 关键行号 + 代码摘录），不确定的标 ❓ 留待核实——沿用《调研素材》的标注约定（✅/⚠️/❓）。
2. **实操验证**：两套环境各跑通一条 E2E 链路，截图/日志留档：
   - west：`pip install west` → `west init` → `west update` → `west build`（选一块 qemu / native_sim 板）→ `west flash --dry-run` → `west boards` → `west sdk` 相关命令；
   - Env：安装 env-windows（或 Linux env）→ `menuconfig` → `pkgs --update` → `scons` → `scons --target=mdk5` 和 `--target=vsc`，检查生成工程文件能否被对应 IDE 工具识别。
3. **三栏映射法**：对比分析统一用"能力 → 实现机制 → 可移植性评估（直接复用 / 改造借鉴 / 仅思路借鉴 / 不借鉴）"四档标注。
4. **网络**：访问 GitHub 走主机 Clash 代理（`127.0.0.1:7890`）；查官方文档时优先 docs.zephyrproject.org、rt-thread.io 一手页面。

---

## 四、阶段划分与产出

| 阶段 | 内容 | 预估工作量 | 产出物 |
|---|---|---|---|
| **P0 准备** | clone 三仓、锁版本、装好两套环境并跑通最小验证 | 0.5 天 | 《调研环境与版本记录.md》（版本号、环境、踩坑） |
| **P1 west 深读** | 按 W1–W9 读码 + 实操，先架构总览（画模块图/数据流图），再逐个子命令深挖，重点投入 W3（扩展）与 W5（runner） | 2–3 天 | 《west 实现机制深度分析.md》 |
| **P2 Env 深读** | 按 E1–E7 读码 + 实操，重点投入 E5（`--target` 导出器）与 E1/E6（Windows 免装） | 1.5–2 天 | 《Env 实现机制深度分析.md》 |
| **P3 对比与映射** | C1 对比矩阵 + LiteOS L0/L1 借鉴映射 + LiteOS 构建工具命令面草案（初判：`liteos build/flash/boards/export/sdk` 之类，含与 GN 主线、CMake 兜底的关系） | 1 天 | 《west与Env机制对比与LiteOS借鉴映射.md》 + 命令面草案章节 |
| **P4 汇报更新** | 将结论回填《汇报最终版.md》或作为附录 | 0.5 天 | 更新后的汇报文档 |

产出物统一放 `Study/` 目录，中文撰写。

---

## 五、关键预判（读码前先立假设，读码后验证/推翻）

> 用"假设驱动"避免读码漫游；每条预判在对应阶段标 ✅ 证实 / ❌ 推翻 / 🔀 部分。

1. west 本体是**纯 Python pip 包**，不含任何构建逻辑；`build/flash` 等命令是 Zephyr 主仓经 `west-commands.yml` 注入的**扩展命令**——即"工具壳"与"领域命令"天然分离（对 LiteOS 最重要的一条架构验证点）。
2. runner 抽象的核心契约在 `ZephyrBinaryRunner` 基类（capabilities: flash/debug/…，do_call 约定），新增一个烧录后端只需继承该类 + 在 runners 注册表登记，代码量预计 < 300 行/后端。
3. Env 的 `--target` 导出器主体是**模板渲染**（BSP 提供模板 + building.py 收集的源文件/宏/分组信息填槽），而非程序化拼 XML；"工程再生" = 重新执行导出命令覆盖旧工程。
4. env-windows 的免装机制本质是 **Python embeddable 包 + 预装 SCons/GCC + `env.cmd` 做一次性 PATH 注入**，无全局安装、无注册表写入。
5. west 的 manifest 机制（projects + import）支撑"按需拉取子集"，是 70GB → 最小源码集减重的可行路径，但需要 LiteOS 侧先把仓库按"内核 / 组件 / 板级 / 工具链预编译物"切分。

---

## 六、风险与开放问题

| 风险/问题 | 影响 | 对策 |
|---|---|---|
| west 与 CMake 深度耦合，LiteOS GN 主线无法直接套 `west build` | 借鉴范围受限 | 明确"参考机制不抄代码"：west 作壳、构建后端经扩展机制插拔；GN 主线保持不动 |
| west 源码在 zephyr 主仓内，clone 体量大 | P0 环境准备慢 | 用浅 clone（`--depth 1`）+ 指定 tag |
| env-windows 为 GPLv2 | 若照抄打包方式需注意许可传染 | 只借鉴机制思路，实现自有化 |
| RT-Thread 文档与代码已发现多处不一致（见调研素材"待核实项"） | 文档结论不可信 | 一律以代码为准，文档仅作线索 |
| L0/L1 双形态（LiteOS-M 无 MMU / LiteOS-A 有 MMU）对构建工具的差异化诉求 | 命令面草案可能要分叉 | P3 阶段对 L0/L1 分别给出命令面与板级配置差异分析 |
