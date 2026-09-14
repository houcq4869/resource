# blackbox_lite 组件 LiteOS 接口 CMSIS-RTOS2 适配评审材料

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 文档名称 | blackbox_lite 组件 LiteOS 接口 CMSIS-RTOS2 适配评审材料 |
| 文档版本 | V1.0 |
| 日期 | 2026-08-27 |
| 评审对象 | 代码仓 `base/hiviewdfx/blackbox_lite` |
| 变更范围 | 共 5 个文件（4 类）：`blackbox_core.c`、`interfaces/native/kits/blackbox_adapter.h`、`interfaces/native/innerkits/blackbox_adapter.h`（两份头文件内容相同，同步修改）、`BUILD.gn`、`bundle.json` |
| 文档目的 | 支撑代码评审（Code Review）与需求追溯 |
| 变更摘要 | mini 系统黑盒组件由 LiteOS `LOS_*` 私有接口迁移至 CMSIS-RTOS2 标准接口（`LOS_Sem* → osSemaphore*`、`LOS_Msleep → osDelay`、`pthread_create → osThreadNew`） |

## 2. 需求背景

### 2.1 专项背景

OpenHarmony 组件去 LiteOS 内核私有接口（`LOS_*`）专项改造，统一要求：

- **small 系统组件**使用 POSIX 接口；
- **mini 系统组件**使用 CMSIS-RTOS2 接口；
- **被 small+mini 共编的组件**：存在分支隔离的，分开适配（small 分支用 POSIX、mini 分支用 CMSIS）；无分支隔离的，共用同一套 POSIX 实现。

### 2.2 本仓适用范围判断

依据 `bundle.json`：

```json
"component": {
    "name": "blackbox_lite",
    "subsystem": "hiviewdfx",
    "adapted_system_type": [ "mini" ],
    ...
}
```

- `adapted_system_type` 仅含 `"mini"` → 本仓为 **mini-only** 组件，无 small+mini 共编场景；
- 结论：**单套 CMSIS-RTOS2 实现，无需 POSIX 分支、无需分支隔离、无需 `#ifdef` 条件编译**；
- 树内引用核查：无任何 small 系统（linux/liteos_a）组件的 BUILD.gn 依赖本仓（仅 WS63 SDK 的预编译 OHOS 库链接清单引用 `libblackbox_lite.a`）。

### 2.3 统一接口替换动作要求

| 原接口 | 替换为 |
|---|---|
| `LOS_Sem*`（创建/等待/释放） | `osSemaphore*` |
| `LOS_Msleep` | `osDelay` |
| `pthread_create` | `osThreadNew` |

## 3. 代码仓分析（改造前基线）

### 3.1 仓库定位

- 名称：`@ohos/blackbox_lite`，版本 3.1，hiviewdfx 子系统"软件黑盒"组件；
- 资源预算（bundle.json 声明）：rom ~10KB，ram ~5KB；
- 依赖：组件依赖 `utils_lite`、`liteos_m`；第三方依赖为空（改造后补充 `cmsis`）。

### 3.2 目录结构（14 个文件）

| 文件 | 分类 | 说明 |
|---|---|---|
| `blackbox_core.c` | 源码（核心） | 模块注册表、错误通知分发、后台日志保存线程（**本次改造唯一涉及逻辑的文件**） |
| `blackbox_adapter.c` | 源码（适配层） | 平台适配接口弱符号实现 + 启动注册，本次不涉及内核接口，不改 |
| `blackbox_detector.c` / `.h` | 源码（检测器） | 事件上传桩接口，不涉及内核接口，不改 |
| `interfaces/native/kits/blackbox.h`、`blackbox_adapter.h` | 公开接口 | 对外 API（kits 版），`blackbox_adapter.h` 删除 LOS_ 声明 |
| `interfaces/native/innerkits/blackbox.h`、`blackbox_adapter.h` | 公开接口 | 与 kits 版内容一致（两份副本），同步修改 |
| `BUILD.gn` | 构建 | 静态库 `blackbox_lite`，本次增加 CMSIS 头文件搜索路径 |
| `bundle.json` | 元数据 | 本次补充第三方依赖 `cmsis` |
| `README_zh.md`、`LICENSE`、`OAT.xml`、`figures/` | 文档/合规 | 不涉及，不改 |

### 3.3 各源文件职责

- **blackbox_core.c**（核心逻辑）：
  - 全局模块注册表：`g_opsList`（`UTILS_DL_LIST` 双向链表，元素 `struct BBoxOps` = 链表节点 + `struct ModuleOps`）；
  - 注册接口：`BBoxRegisterModuleOps`——查重 + 尾插（信号量保护）；
  - 错误通知接口：`BBoxNotifyError`——按模块名分发 `Dump`/`Reset` 回调或落盘上传，支持 `needSysReset` 复位路径；
  - 后台线程：`SaveErrorLog`——遍历注册模块执行 `GetLastLogInfo`/`SaveLastLog` 保存故障日志；
  - 启动入口：`BBoxInit`（`CORE_INIT_PRI(..., 1)`）——创建信号量与后台线程。
- **blackbox_adapter.c**（平台适配层）：提供 7 个 `WEAK` 平台适配接口默认实现（`SystemModuleDump`/`Reset`/`GetLastLogInfo`/`SaveLastLog`/`FullWriteFile`/`GetFaultLogPath`/`RebootSystem`），并在 `CORE_INIT_PRI(..., 2)` 注册 `MODULE_SYSTEM` 模块。
- **blackbox_detector.c/.h**：`UploadEventByFile`/`UploadEventByStream` 上传桩。

### 3.4 构建与依赖

- `BUILD.gn`：`static_library("blackbox_lite")`，`deps = []`，include_dirs 指向本仓、hiview_lite、hilog_lite、utils_lite；
- 树内实际编译该仓的产品：**nearlink_dk_3863**（HiSilicon WS63，liteos_m，预编译内核）；
- 无外部 BUILD.gn 依赖本仓（全树 grep 确认）。

## 4. 整体逻辑功能

### 4.1 启动流程时序

```
WS63 main()
  └─ osKernelInitialize()            // = LOS_KernelInit()
  └─ OHOS_SystemInit()               // 遍历 .zinitcall 段，调用 CORE_INIT 注册函数
       ├─ CORE_INIT_PRI(BBoxInit, 1)      // 创建信号量 + 创建 SaveErrorLog 线程（仅注册，调度器启动后运行）
       └─ CORE_INIT_PRI(BBoxAdapterInit, 2) // 注册 MODULE_SYSTEM（内部 Acquire 信号量，令牌可用立即返回）
  └─ osKernelStart()                 // = LOS_Start()，SaveErrorLog 线程开始运行
```

### 4.2 模块注册机制

`BBoxRegisterModuleOps(ops)`：malloc 分配 `BBoxOps` 节点 → 复制 `ModuleOps` → Acquire 信号量进入临界区 →
遍历 `g_opsList` 按 `module` 名查重（重复则释放信号量返回 -1）→ 尾插链表 → 释放信号量返回 0。

### 4.3 错误上报机制

`BBoxNotifyError(event, module, errorDesc, needSysReset)`：

- `needSysReset == 0`：延时等待日志根目录就绪 → **非阻塞** Acquire 信号量（失败仅打日志并返回）→ 按模块名查找 →
  找到后 `Dump` 回调（若注册）/`Reset` 回调（若注册）/`SaveBasicErrorInfo` 落盘+上传（两者都未注册时）→ 释放信号量；
- `needSysReset != 0`：不加锁直接执行 `Dump`/`Reset` 回调，处理完调用 `RebootSystem()`（锁保护被有意绕过，复位路径不释放锁）。

### 4.4 后台保存线程

`SaveErrorLog` 线程体：malloc `ErrorInfo` → 等待日志根目录 → **阻塞** Acquire 信号量 → 遍历注册模块执行
`GetLastLogInfo`/`SaveLastLog` 保存各模块故障日志并上传 → 释放信号量 → free 后退出（一次性任务线程）。

### 4.5 同步机制

单一二元信号量 `g_opsListSem`（初值 1）保护 `g_opsList` 链表的三个访问点：注册路径（阻塞获取）、
错误通知路径（非阻塞获取）、后台保存路径（阻塞获取）。信号量初始状态"令牌可用"，
`BBoxAdapterInit` 在调度器启动前的首次 Acquire 立即成功返回，不涉及阻塞。

### 4.6 平台适配接口（与本次改造无关，保持不动）

7 个 `WEAK` 接口：`SystemModuleDump`、`SystemModuleReset`、`SystemModuleGetLastLogInfo`、
`SystemModuleSaveLastLog`、`FullWriteFile`、`GetFaultLogPath`、`RebootSystem`——由具体平台（如 hi3861 SDK）覆写实现。

## 5. 改造前存在的问题（相对需求）

### 5.1 偏离点清单（全部集中在 blackbox_core.c）

| 类别 | 接口 | 处数 | 改造前位置 |
|---|---|---|---|
| LOS 信号量创建 | `LOS_BinarySemCreate(1, &sem)` | 1 | BBoxInit |
| LOS 信号量阻塞等待 | `LOS_SemPend(sem, LOS_WAIT_FOREVER)` | 2 | SaveErrorLog、BBoxRegisterModuleOps |
| LOS 信号量非阻塞等待 | `LOS_SemPend(sem, LOS_NO_WAIT)` | 1 | BBoxNotifyError |
| LOS 信号量释放 | `LOS_SemPost(sem)` | 4 | 上述三处临界区出口 |
| LOS 延时 | `LOS_Msleep(1000)` | 1 | WaitForLogRootDir |
| POSIX 线程创建 | `pthread_create(&taskId, NULL, SaveErrorLog, NULL)` | 1 | BBoxInit |
| POSIX 头文件 | `#include "pthread.h"` | 1 | 文件头 |
| LOS 常量兜底宏 | 局部 `#ifndef` 定义 `LOS_WAIT_FOREVER/LOS_NO_WAIT/LOS_OK` | 1 组 | 文件头 |

### 5.2 公开接口污染

`interfaces/native/kits/blackbox_adapter.h` 与 `interfaces/native/innerkits/blackbox_adapter.h`（两份内容相同的公开头）中，
以"内核已实现"为名直接声明了 3 个内核函数：

```c
/* The following functions have been implemented in the kernel */
extern unsigned int LOS_BinarySemCreate(unsigned short count, unsigned int *semHandle);
extern unsigned int LOS_SemPend(unsigned int semHandle, unsigned int timeout);
extern unsigned int LOS_SemPost(unsigned int semHandle);
```

该声明实为内核头文件（`los_sem.h`）声明的复制，不属于黑盒组件对外 API，属公开接口泄漏。

### 5.3 问题归纳（与需求对照）

1. **违反专项统一要求**：mini 组件应使用 CMSIS-RTOS2，本仓直接调用 LiteOS `LOS_*` 私有接口；
2. **可移植性受限**：依赖具体内核私有接口，更换内核需改源码（专项改造的目标即消除此类依赖）；
3. **接口风格不统一**：`pthread_create` 与 `LOS_*` 混用（线程用 POSIX、同步用内核私有接口）；
4. **公开头泄漏内核声明**：对外头文件复制内核函数声明，污染 API 面；
5. **兜底宏冗余**：局部 `#ifndef` 定义 `LOS_WAIT_FOREVER` 等内核常量，属兼容脚手架残留。

### 5.4 改造可行性前置结论（计划阶段已验证，含证据）

| 结论 | 证据 |
|---|---|
| 树内核 LiteOS-M 完整实现 CMSIS-RTOS2 | `kernel/liteos_m/kal/cmsis/cmsis_liteos2.c`（osThreadNew:246 / osDelay:643 / osSemaphoreNew:1120），`KAL_CMSIS` Kconfig 默认 y |
| WS63 预编译内核提供全部所需符号 | 固件符号清单 `ws63-liteos-app.lst` 中确认 `osSemaphoreNew/Acquire/Release`、`osThreadNew`、`osDelay`、`osKernelGetTickFreq` 均已实现（platform 预编译库） |
| CORE_INIT 阶段调用安全 | 树内核 `osSemaphoreNew` → `LOS_BinarySemCreate/LOS_SemCreate`（纯资源创建）；`osThreadNew` → `LOS_TaskCreate`（`g_taskScheduled` 为假时仅入队，`LOS_Start` 后运行） |
| osDelay 语义 | 仅在运行时路径（BBoxNotifyError、SaveErrorLog 线程体）被调用；调度器启动后 `osDelay` 等价任务延时 |
| 公开头清理无副作用 | hi3861 使用 SDK 自有 `hi_blackbox*.h`，全树无组件依赖本仓公开头中的 LOS_ 声明 |

## 6. 接口改造详细方案

### 6.1 改造总原则

1. mini-only 单套 CMSIS-RTOS2 实现，不引入 `#ifdef` 分支；
2. **保持既有逻辑语义与错误处理路径不变**（逐项等价性分析见 6.5）；
3. 对外公开接口（`BBoxRegisterModuleOps`/`BBoxNotifyError`/`struct ModuleOps` 等）零变化；
4. 编译告警零新增（`-Wall -Wextra` 下验证）。

### 6.2 逐接口改造表（组件：blackbox_lite）

**文件一：`blackbox_core.c`（改造前 333 行 → 改造后 323 行）**

| # | 改造后行号 | 原接口调用 | 改造后接口调用 | 修改方案 |
|---|---|---|---|---|
| 1 | 19 | `#include "pthread.h"` | `#include "cmsis_os2.h"` | 头文件替换 |
| 2 | 26-28 | 局部定义 `LOS_WAIT_FOREVER=0xFFFFFFFF`/`LOS_NO_WAIT=0`/`LOS_OK=0` 兜底宏 | 删除；新增 `#define BLACKBOX_TASK_STACK_SIZE 0x1000` | 删除内核常量复制，新增线程栈宏 |
| 3 | 39 | `static unsigned int g_opsListSem;` | `static osSemaphoreId_t g_opsListSem;` | 信号量句柄类型改为 CMSIS 句柄 |
| 4 | 99 | `LOS_Msleep(LOG_ROOT_DIR_WAIT_TIME);` | `osDelay(LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / 1000);` | 延时迁移，tick 换算 |
| 5 | 135 | `static void* SaveErrorLog(void *param)` | `static void SaveErrorLog(void *param)` | 线程函数签名匹配 `osThreadFunc_t`；体内 `return NULL;` → `return;` |
| 6 | 150 | `LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0` | `osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK` | 阻塞等待迁移 |
| 7 | 177 | `(void)LOS_SemPost(g_opsListSem);` | `(void)osSemaphoreRelease(g_opsListSem);` | 释放迁移 |
| 8 | 214 | `LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0` | `osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK` | 阻塞等待迁移 |
| 9 | 225 | `(void)LOS_SemPost(g_opsListSem);` | `(void)osSemaphoreRelease(g_opsListSem);` | 释放迁移（重复注册失败路径） |
| 10 | 234 | `(void)LOS_SemPost(g_opsListSem);` | `(void)osSemaphoreRelease(g_opsListSem);` | 释放迁移（注册成功路径） |
| 11 | 261 | `LOS_SemPend(g_opsListSem, LOS_NO_WAIT) != 0` | `osSemaphoreAcquire(g_opsListSem, 0U) != osOK` | 非阻塞等待迁移 |
| 12 | 294 | `(void)LOS_SemPost(g_opsListSem);` | `(void)osSemaphoreRelease(g_opsListSem);` | 释放迁移 |
| 13 | 308-323 | `LOS_BinarySemCreate(1, &g_opsListSem) != LOS_OK` + `pthread_create(&taskId, NULL, SaveErrorLog, NULL)` | `g_opsListSem = osSemaphoreNew(1, 1, NULL)` + `osThreadNew(SaveErrorLog, NULL, &taskAttr)` | 信号量/线程创建迁移，见下方代码对比 |

**改造前 BBoxInit（原 318-333 行）：**

```c
static void BBoxInit(void)
{
    int ret = -1;
    pthread_t taskId = 0;

    if (LOS_BinarySemCreate(1, &g_opsListSem) != LOS_OK) {
        BBOX_PRINT_ERR("Create binary semaphore failed!\n");
        return;
    }
    UtilsListInit(&g_opsList);
    ret = pthread_create(&taskId, NULL, SaveErrorLog, NULL);
    if (ret != 0) {
        BBOX_PRINT_ERR("Falied to create SaveErrorLog task, ret: %d\n", ret);
    }
}
CORE_INIT_PRI(BBoxInit, 1);
```

**改造后 BBoxInit（308-323 行）：**

```c
static void BBoxInit(void)
{
    osThreadAttr_t taskAttr = {
        "BlackBoxTask", 0, NULL, 0, NULL, BLACKBOX_TASK_STACK_SIZE, osPriorityNormal, 0, 0
    };

    g_opsListSem = osSemaphoreNew(1, 1, NULL);
    if (g_opsListSem == NULL) {
        BBOX_PRINT_ERR("Create binary semaphore failed!\n");
        return;
    }
    UtilsListInit(&g_opsList);
    if (osThreadNew(SaveErrorLog, NULL, &taskAttr) == NULL) {
        BBOX_PRINT_ERR("Failed to create SaveErrorLog task!\n");
    }
}
CORE_INIT_PRI(BBoxInit, 1);
```

**改造前 WaitForLogRootDir 循环体（原 106-108 行）：**

```c
    while (i++ < LOG_ROOT_DIR_WAIT_COUNT) {
        LOS_Msleep(LOG_ROOT_DIR_WAIT_TIME);
    }
```

**改造后（98-100 行）：**

```c
    while (i++ < LOG_ROOT_DIR_WAIT_COUNT) {
        osDelay(LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / 1000);
    }
```

### 6.3 关键映射细节专述

1. **信号量创建**：`LOS_BinarySemCreate(1, &sem)` → `osSemaphoreNew(1U, 1U, NULL)`。
   CMSIS 语义 `max_count == 1` 即二元信号量——树内核实现中 `max_count == 1` 时直接调用 `LOS_BinarySemCreate`，
   与原来走同一内核原语；初始计数值 1 保持"创建后令牌可用"的既有状态。
   成功判定由 `!= LOS_OK` 改为句柄 `== NULL`（失败模式唯一，布尔语义等价）。

2. **阻塞等待**：`LOS_SemPend(sem, LOS_WAIT_FOREVER)` → `osSemaphoreAcquire(sem, osWaitForever)`。
   `osWaitForever` 定义值 `0xFFFFFFFFU` 与原局部宏数值完全一致；CMSIS 成功返回 `osOK`(0)，
   失败返回 `osErrorParameter`/`osErrorResource`/`osErrorTimeout`（均非零）——
   原判错 `!= 0` 改为 `!= osOK` 后成功/失败分支完全一致。

3. **非阻塞等待**：`LOS_SemPend(sem, LOS_NO_WAIT)` → `osSemaphoreAcquire(sem, 0U)`。
   `LOS_NO_WAIT == 0`；CMSIS 超时 0 严格非阻塞——有令牌返回 `osOK`，无令牌返回 `osErrorTimeout`（非零）。
   `BBoxNotifyError` 失败分支（打日志 → goto __out → free → 返回）逐语句保持。

4. **信号量释放**：`LOS_SemPost` → `osSemaphoreRelease`。4 处释放点均存在"同函数内成功 Acquire 前置"
   （SaveErrorLog、BBoxRegisterModuleOps 两条路径、BBoxNotifyError 受 `needSysReset == 0` 门控），
   不存在"信号量满员仍释放"的可达路径，两个 API 的 `SEM_OVERFLOW`/`osErrorResource` 差异均不可达。

5. **延时**：`LOS_Msleep(ms)` → `osDelay(tick)`。CMSIS `osDelay` 参数为 **tick 数**而非毫秒，
   故按内核 tick 频率换算：`LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / 1000`。
   WS63 内核 1000Hz → 1000 ticks = 1000ms；树内核 qemu riscv32 产品 100Hz → 100 ticks = 1000ms。
   运算量级（1000 × 1000 = 1e6）远小于 `uint32_t` 上限，无溢出。

6. **线程创建**：`pthread_create(&taskId, NULL, SaveErrorLog, NULL)` →
   `osThreadNew(SaveErrorLog, NULL, &taskAttr)`。
   - `SaveErrorLog` 原签名 `void* (*)(void*)` 与 `osThreadFunc_t`（`void (*)(void*)`）不兼容
     （直接传入会触发 `-Wall` 下 incompatible-pointer-types 告警），故签名改为 `void`；
   - `osThreadAttr_t` 按位序初始化九字段 `{name, attr_bits, cb_mem, cb_size, stack_mem, stack_size,
     priority, tz_module, reserved}`（与树内 samgr_lite CMSIS 适配器 `thread_adapter.c` 风格一致）：
     名称 `"BlackBoxTask"`、栈 `0x1000`（SaveErrorLog 使用 malloc 堆缓冲 + 256B 局部 `dirName`，
     4KB 远大于树内核默认 0x400，且在 bundle.json ~5KB RAM 预算内）、优先级 `osPriorityNormal`(24)
     （与 LiteOS 默认任务优先级一致）；
   - 时序等价：BBoxInit 运行于 `osKernelStart()` 之前，`osThreadNew` 仅注册任务、调度器启动后线程体才运行，
     与原 `pthread_create` 行为一致；失败处理由"打印 ret"改为"句柄 `== NULL` 判失败打印"，均不回滚启动。

### 6.4 头文件/声明改造

**文件二/三：`interfaces/native/kits/blackbox_adapter.h`、`interfaces/native/innerkits/blackbox_adapter.h`**
（两份内容相同，52 行 → 46 行，同步修改）

删除（原 41-44 行）：

```c
/* The following functions have been implemented in the kernel */
extern unsigned int LOS_BinarySemCreate(unsigned short count, unsigned int *semHandle);
extern unsigned int LOS_SemPend(unsigned int semHandle, unsigned int timeout);
extern unsigned int LOS_SemPost(unsigned int semHandle);
```

其余内容（`WEAK` 宏、7 个平台适配接口 extern、`extern "C"` 包裹）全部保持。

### 6.5 构建集成改造

**文件四：`BUILD.gn`**（26 行）

```gn
  include_dirs = [
    "//third_party/cmsis/CMSIS/RTOS2/Include",   # 新增，放首位
    "//base/hiviewdfx/blackbox_lite",
    ...
  ]
```

设计要点：
- 组件 include_dirs 在编译命令中位于板级/SDK 目录之前（已在生成 ninja 中实证），
  引用的 `cmsis_os2.h` 稳定命中 `//third_party/cmsis` 源码仓（各 SDK 副本为同源同构，见 8.1）；
- **不新增 `//kernel/liteos_m` 依赖**：nearlink_dk_3863 等 mini 产品使用预编译内核
  （vendor config `kernel_is_prebuilt: true`），依赖树内核目标会误将树内核拉入构建。

**文件五：`bundle.json`**（27 行）

```json
"third_party": [ "cmsis" ]   // 原为 []
```

组件名 `cmsis` 已在 `third_party/cmsis/bundle.json` 中注册（subsystem: thirdparty）。纯元数据变更，无编译影响。

### 6.6 错误处理等价性分析表

| LOS/pthread 调用 | CMSIS 调用 | 成功语义 | 失败语义 | 行为是否变化 |
|---|---|---|---|---|
| `LOS_BinarySemCreate(1,&sem) != LOS_OK` | `osSemaphoreNew(1,1,NULL) == NULL` | 创建二元信号量，初始令牌可用 | 资源耗尽返回失败，BBoxInit 直接 return | 否（唯一失败模式） |
| `LOS_SemPend(sem, WAIT_FOREVER) != 0` ×2 | `Acquire(sem, osWaitForever) != osOK` | 永久阻塞至令牌可用 | 参数错/资源错（原 `!=0` 捕获一切非零） | 否 |
| `LOS_SemPend(sem, NO_WAIT) != 0` ×1 | `Acquire(sem, 0U) != osOK` | 立即获取令牌 | 无令牌返回 `osErrorTimeout`，走原失败分支 | 否 |
| `LOS_SemPost(sem)` ×4 | `osSemaphoreRelease(sem)` | 令牌 +1 | 满员溢出（本仓不可达） | 否 |
| `LOS_Msleep(1000)` | `osDelay(1000*freq/1000)` | 任务延时 1000ms | —（返回码均被丢弃） | 否 |
| `pthread_create(...) != 0` | `osThreadNew(...) == NULL` | 创建一次性后台任务 | 创建失败仅打印，不阻断启动 | 否 |

### 6.7 明确不改清单

| 对象 | 原因 |
|---|---|
| `BBoxDriverInit` 死声明（blackbox.h 两份） | 超出本次适配范围，评审决策保留 |
| `blackbox_adapter.c` / `blackbox_detector.c` / `blackbox.h` | 不涉及内核接口 |
| `README_zh.md` / `OAT.xml` / `LICENSE` | 不涉及 |
| 树内其他产品 config（如 qemu demo） | 本仓非其编译部件，不扩验证范围（评审决策） |

## 7. 验证方案与结果

### 7.1 验证环境

| 项 | 值 |
|---|---|
| 平台 | WSL2 + Ubuntu（Linux 6.18.33.2-microsoft-standard-WSL2） |
| 构建工具 | hb（ohos-env pyenv）、GN + ninja（prebuilts/build-tools） |
| 工具链 | WS63 riscv32-linux-musl-gcc 7.3.0（build ver102.010 2024-04-2，`cc_riscv32_musl_fp` 变体，~/.bashrc PATH 配置） |
| 产品 | nearlink_dk_3863（liteos_m / WS63 预编译内核，ccache 开启） |

### 7.2 构建结果

```
[OHOS INFO]   build success
[OHOS INFO]  Cost Time:  0:00:57
c overall build overlap rate: 1.00   （exit 0）

（后续环境修复后的复验构建同样成功：exit 0 / 0:00:55，结论一致）
```

### 7.3 静态符号验证（riscv32-linux-musl-nm 扫描 libblackbox_lite.a）

| 检查项 | 结果 |
|---|---|
| `los_` 符号残留 | **0 个**（LOS_Sem/LOS_Msleep/LOS_BinarySem 全部消失） |
| `osSemaphoreNew` / `osSemaphoreAcquire` / `osSemaphoreRelease` | 均为 `U`（未定义符号） |
| `osThreadNew` / `osDelay` / `osKernelGetTickFreq` | 均为 `U`（未定义符号） |

6 个 CMSIS 符号全部由 WS63 预编译内核解析（其存在于固件符号清单 `ws63-liteos-app.lst` 中已提前核实），
最终 SDK 链接成功即证明全部解析。

### 7.4 include 路径顺序验证

重新生成的 `obj/base/hiviewdfx/blackbox_lite/blackbox_lite.ninja` 中：

```
include_dirs = -I.../base/hiviewdfx/blackbox_lite ...
  第 3 位:  -I.../third_party/cmsis/CMSIS/RTOS2/Include     ← 新增目录
  第 35 位: -I.../Huawei_LiteOS/compat/cmsis                ← SDK 副本，顺序在后
```

新增目录先于 SDK 各 cmsis 目录，头文件命中符合预期。

### 7.5 产物链验证

| 产物 | 时间戳 | 说明 |
|---|---|---|
| `obj/base/hiviewdfx/blackbox_lite/*.o` ×3 | 17:24 | 改造后源码重新编译 |
| `libs/libblackbox_lite.a` | 17:24 | 静态库归档 |
| `ws63-liteos-app-sign.bin` | 17:24 | SDK 用新库重链固件 |
| `ws63-liteos-app/ws63-liteos-app_all.fwpkg` | 17:24（17:50 修复重编后再次生成） | 烧录包生成 |
| `ws63-liteos-app/ws63-liteos-app_load_only.fwpkg` | 同上 | 烧录包生成 |

### 7.6 运行时说明

- 本产品中 `BBoxNotifyError` 无调用方（全树 grep 为 0 处），错误通知路径按设计处于休眠状态；
- 启动期真实执行的路径：`BBoxInit`（创建信号量/线程）与 `BBoxAdapterInit`（注册 SYSTEM 模块，
  内部执行一次成功的非阻塞 Acquire/Release）；
- 以上路径在固件启动时随 CORE_INIT 执行，编译链接层面已验证，运行层面无新增风险点（见 8.1）。

## 8. 风险评估与遗留事项

### 8.1 风险与对策

| # | 风险 | 分析 | 对策/结论 |
|---|---|---|---|
| 1 | 头文件遮蔽（多个 cmsis_os2.h 副本） | WS63 SDK 含多个同源副本；本仓新增 include 目录优先命中 `third_party/cmsis` 版本；各副本 `osThreadAttr_t` 字段布局、原型、`osPriorityNormal` 值一致（已 diff 核实） | 已在生成 ninja 中验证 -I 顺序；即便顺序反转亦无 ABI 差异 |
| 2 | 启动前 osDelay 语义退化 | 树内核实现中调度器启动前 `osDelay` 退化为空 `HalDelay` 桩 | 本仓 `WaitForLogRootDir` 仅在运行时路径（BBoxNotifyError、SaveErrorLog 线程体）调用，不受影响；文档约束：`BBoxNotifyError` 不得从 CORE_INIT 钩子调用 |
| 3 | 信号量句柄类型变化 | `unsigned int` → `osSemaphoreId_t`(void*) | 全部引用位于 blackbox_core.c 内部；公开头 LOS_ extern 声明同批删除，无类型泄漏面 |
| 4 | 线程栈/优先级选值 | 栈 0x1000、osPriorityNormal(24) | SaveErrorLog 栈用量 = 256B dirName + 少量局部变量（缓冲区均 malloc 堆分配），4KB 充足且在 ~5KB RAM 预算内；优先级与原 LiteOS 默认任务优先级一致 |
| 5 | 编译告警面 | `void*(*)(void*)` 传 `osThreadNew` 会告警 | 已通过 SaveErrorLog 签名改为 `void` 规避，`-Wall -Wextra` 下零新增告警 |

### 8.2 遗留事项

1. **`BBoxDriverInit` 死声明**：公开头中声明但全树无实现/无调用，评审决策保留，后续另行清理；
2. **树内核路径未做编译验证**：当前无任何产品使用树内核（kernel/liteos_m）编译本仓
   （qemu riscv32 demo 的 hiviewdfx 部件列表不含 blackbox_lite），评审决策不做产品级扩展验证；
   树内核 kal/cmsis 的 API 完备性已通过源码级核对（cmsis_liteos2.c 实现齐全）；
3. **hiviewdfx 其他仓的 LOS_ 残留**（如 hiview_lite 的 `LOS_IntLock`）：超出本仓范围，建议专项统一推进。

## 9. 附录

### 附录 A：涉及文件清单与改动统计

| 文件 | 改动 | 净变化 |
|---|---|---|
| `base/hiviewdfx/blackbox_lite/blackbox_core.c` | LOS_*/pthread → CMSIS-RTOS2 | 333 行 → 323 行 |
| `base/hiviewdfx/blackbox_lite/interfaces/native/kits/blackbox_adapter.h` | 删除 3 行 LOS_ extern | 52 行 → 46 行 |
| `base/hiviewdfx/blackbox_lite/interfaces/native/innerkits/blackbox_adapter.h` | 同上（副本同步） | 52 行 → 46 行 |
| `base/hiviewdfx/blackbox_lite/BUILD.gn` | include_dirs +1 行 | 32 行 → 33 行 |
| `base/hiviewdfx/blackbox_lite/bundle.json` | third_party 补充 cmsis | 2 行 |

### 附录 B：接口映射速查表

| 原接口 | 新接口 | 备注 |
|---|---|---|
| `LOS_BinarySemCreate(count, &handle)` | `osSemaphoreNew(max, initial, NULL)` | max=1 即二元信号量；句柄返回值式 |
| `LOS_SemPend(handle, LOS_WAIT_FOREVER)` | `osSemaphoreAcquire(handle, osWaitForever)` | 0xFFFFFFFFU 数值一致 |
| `LOS_SemPend(handle, LOS_NO_WAIT)` | `osSemaphoreAcquire(handle, 0U)` | 0 超时 = 非阻塞 |
| `LOS_SemPost(handle)` | `osSemaphoreRelease(handle)` | — |
| `LOS_Msleep(ms)` | `osDelay(ms * osKernelGetTickFreq() / 1000)` | tick 换算 |
| `pthread_create(&tid, NULL, fn, arg)` | `osThreadNew(fn, arg, &attr)` | 线程函数签名 `void(*)(void*)` |

### 附录 C：引用标准与实现

- CMSIS-RTOS2 API 规范：`third_party/cmsis/CMSIS/RTOS2/Include/cmsis_os2.h`
- LiteOS-M KAL CMSIS 实现：`kernel/liteos_m/kal/cmsis/cmsis_liteos2.c`
- 树内同类先例：`foundation/systemabilitymgr/samgr_lite/samgr/adapter/cmsis/thread_adapter.c`
  （osThreadAttr_t 位序初始化风格参照）、`base/hiviewdfx/hiview_lite/hiview_util.c`（hiviewdfx 子系统已迁移先例）

### 附录 D：评审关注点清单

1. 语义等价性：6.5 表逐项核对（重点：0 超时非阻塞、osWaitForever 数值、释放前置条件）；
2. 时序安全：CORE_INIT 阶段 `osSemaphoreNew`/`osThreadNew` 的启动前行为（5.4 已核）；
3. include 策略：新增 `//third_party/cmsis` 目录的优先级与不依赖树内核的原因（6.5）；
4. 公开接口变化：仅删除内核声明，组件自身 API 零变化（6.4）；
5. 告警面：SaveErrorLog 签名变更的必要性（6.3-6）。
