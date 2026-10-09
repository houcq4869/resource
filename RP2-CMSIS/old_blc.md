# blackbox_lite 组件 LOS 内核接口 CMSIS-RTOS2 适配修改方案

| 项目 | 内容 |
| --- | --- |
| 组件名称 | blackbox_lite（`@ohos/blackbox_lite`，hiviewdfx 子系统） |
| 组件仓库路径 | `base/hiviewdfx/blackbox_lite` |
| 适配类型 | LOS_ 接口 → CMSIS-RTOS2（mini 系统组件按需求统一走 CMSIS 路线） |
| 文档状态 | 修改方案（计划阶段，未实施代码修改） |
| 文档日期 | 2026-08-27 |

---

## 1. 背景与目标

### 1.1 需求背景

OpenHarmony 正在统一将各组件中直接使用 LiteOS 内核 `LOS_*` 接口的调用点，适配为标准的 POSIX / CMSIS 接口：

- **small 系统组件**：使用 POSIX 接口；
- **mini 系统组件**：使用 CMSIS-RTOS2 接口（`cmsis_os2.h`）；
- **small + mini 共编译的组件**：存在分支隔离则分别适配；无分支隔离则共用同一套 POSIX。

本次适配统一动作（偏离点映射规则）：

| 原接口（LiteOS 内核） | 目标接口（CMSIS-RTOS2） |
| --- | --- |
| `LOS_Sem*`（`LOS_BinarySemCreate` / `LOS_SemPend` / `LOS_SemPost`） | `osSemaphore*`（`osSemaphoreNew` / `osSemaphoreAcquire` / `osSemaphoreRelease`） |
| `LOS_Msleep` | `osDelay` |
| `pthread_create` | `osThreadNew` |

### 1.2 本组件形态判定

依据 `bundle.json` 中的组件元信息：

```json
"component": {
    "name": "blackbox_lite",
    "subsystem": "hiviewdfx",
    "adapted_system_type": [
        "mini"
    ],
    "deps": {
        "components": [
            "utils_lite",
            "liteos_m"
        ],
        ...
```

判定结论：

1. **本组件仅适配 mini 系统**（`adapted_system_type: ["mini"]`），不参与 small 系统编译；
2. 因此**整仓统一采用 CMSIS-RTOS2 路线**，不引入 POSIX 实现，也不存在 small/mini 分支隔离的需求；
3. 依赖 `liteos_m` 保持不变——CMSIS-RTOS2 运行时（`kernel/liteos_m/kal/cmsis` 的 CMSIS KAL 层）即由 liteos_m 内核提供。

### 1.3 接口头文件来源

- 目标头文件：`cmsis_os2.h`，在 mini 构建环境中由 `kernel/liteos_m/kal/cmsis/cmsis_os2.h` 提供（该文件透传包含 `third_party/cmsis/CMSIS/RTOS2/Include/cmsis_os2.h` 标准头）；
- 该头文件由内核 CMSIS KAL 模块的 public config 暴露，受内核配置项 `LOSCFG_KAL_CMSIS` 门控（liteos_m bundle 的 `sub_component` 中已含 `cmsis`，mini 标准配置默认开启）。

---

## 2. 偏离点全景清单

经全仓扫描（`grep -rn "LOS_\|pthread"`），本仓 LOS/POSIX 线程接口的使用点分布如下：

| 序号 | 文件 | 行号 | 现状调用 | 分类 |
| --- | --- | --- | --- | --- |
| 1 | `blackbox_core.c` | 21 | `#include "pthread.h"` | 头文件 |
| 2 | `blackbox_core.c` | 28-36 | 本地宏 `LOS_WAIT_FOREVER` / `LOS_NO_WAIT` / `LOS_OK` | 宏定义 |
| 3 | `blackbox_core.c` | 47 | `static unsigned int g_opsListSem;` | 变量类型 |
| 4 | `blackbox_core.c` | 107 | `LOS_Msleep(LOG_ROOT_DIR_WAIT_TIME)` | 延时 |
| 5 | `blackbox_core.c` | 143, 161, 188 | `static void* SaveErrorLog(void *param)` 及 `return NULL;`×2 | 线程函数签名 |
| 6 | `blackbox_core.c` | 158, 224 | `LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER)` | 信号量 |
| 7 | `blackbox_core.c` | 271 | `LOS_SemPend(g_opsListSem, LOS_NO_WAIT)` | 信号量 |
| 8 | `blackbox_core.c` | 185, 235, 244, 304 | `LOS_SemPost(g_opsListSem)` | 信号量 |
| 9 | `blackbox_core.c` | 321, 328-331 | `pthread_t taskId` + `pthread_create(&taskId, NULL, SaveErrorLog, NULL)` | 线程创建 |
| 10 | `blackbox_core.c` | 323 | `LOS_BinarySemCreate(1, &g_opsListSem)` | 信号量创建 |
| 11 | `interfaces/native/kits/blackbox_adapter.h` | 41-44 | `extern LOS_BinarySemCreate/LOS_SemPend/LOS_SemPost` 声明（残留） | 头文件残留 |
| 12 | `interfaces/native/innerkits/blackbox_adapter.h` | 41-44 | 同上（两份头文件内容完全一致） | 头文件残留 |

**说明**：`blackbox_adapter.c`、`blackbox_detector.c` 及 `interfaces` 下其余头文件不包含任何 LOS/pthread 调用，无需修改。全部改动集中在 `blackbox_core.c`（10 处）+ 两份 `blackbox_adapter.h`（各 1 处，共 12 个修改点）。

---

## 3. 修改方案总览（组件 → 文件 → 接口 → 动作）

| 组件 | 文件 | 原接口 | 修改动作 |
| --- | --- | --- | --- |
| blackbox_lite | `blackbox_core.c` | `#include "pthread.h"` | 替换为 `#include "cmsis_os2.h"` |
| blackbox_lite | `blackbox_core.c` | `LOS_WAIT_FOREVER` / `LOS_NO_WAIT` / `LOS_OK` 本地宏 | 删除，改用 CMSIS 常量 `osWaitForever` / `0U` / `osOK` |
| blackbox_lite | `blackbox_core.c` | `unsigned int g_opsListSem` | 改为 `osSemaphoreId_t g_opsListSem = NULL` |
| blackbox_lite | `blackbox_core.c` | `LOS_Msleep(1000)` | 改为 `osDelay(1000)` |
| blackbox_lite | `blackbox_core.c` | `void* SaveErrorLog(void*)` | 改为 `void SaveErrorLog(void *)`（`osThreadFunc_t` 签名） |
| blackbox_lite | `blackbox_core.c` | `LOS_SemPend(sem, 0xFFFFFFFF)` / `LOS_SemPend(sem, 0)` | 改为 `osSemaphoreAcquire(sem, osWaitForever)` / `osSemaphoreAcquire(sem, 0U)` |
| blackbox_lite | `blackbox_core.c` | `LOS_SemPost(sem)` | 改为 `osSemaphoreRelease(sem)` |
| blackbox_lite | `blackbox_core.c` | `LOS_BinarySemCreate(1, &sem)` | 改为 `osSemaphoreNew(1, 1, NULL)` |
| blackbox_lite | `blackbox_core.c` | `pthread_create(&tid, NULL, fn, NULL)` | 改为 `osThreadNew(fn, NULL, &attr)`（显式线程属性） |
| blackbox_lite | `interfaces/native/kits/blackbox_adapter.h` | 3 个 `extern LOS_*` 声明 | 整段删除 |
| blackbox_lite | `interfaces/native/innerkits/blackbox_adapter.h` | 3 个 `extern LOS_*` 声明 | 整段删除 |

---

## 4. 逐文件逐接口详细修改方案

### 4.1 `blackbox_core.c`（核心文件，10 个修改点）

#### 4.1.1 修改点 1：头文件包含（第 21 行）

**现状代码（第 16-23 行）：**

```c
#include "blackbox.h"
#include "blackbox_adapter.h"
#include "blackbox_detector.h"
#include "ohos_init.h"
#include "ohos_types.h"
#include "pthread.h"
#include "securec.h"
#include "utils_list.h"
```

**修改后：**

```c
#include "blackbox.h"
#include "blackbox_adapter.h"
#include "blackbox_detector.h"
#include "ohos_init.h"
#include "ohos_types.h"
#include "cmsis_os2.h"
#include "securec.h"
#include "utils_list.h"
```

**详细解释：**

- 删除 `#include "pthread.h"`：文件中唯一的 pthread 用法（`pthread_create` / `pthread_t`）将在修改点 5、9 中替换为 CMSIS 接口，不再依赖 POSIX 线程库；
- 新增 `#include "cmsis_os2.h"`：CMSIS-RTOS2 标准接口头文件，提供本文档全部目标接口（`osSemaphoreNew` / `osSemaphoreAcquire` / `osSemaphoreRelease` / `osDelay` / `osThreadNew`）及常量（`osOK` / `osWaitForever`）。在 mini 构建环境中由 `kernel/liteos_m/kal/cmsis` 的 public config 提供头文件搜索路径（见第 1.3 节），若编译期报找不到头文件，按第 6 节方案在 `BUILD.gn` 中兜底追加 include 路径；
- 其余头文件（`ohos_init.h`、`ohos_types.h`、`utils_list.h` 等）与本适配无关，保持不变。

#### 4.1.2 修改点 2：本地 LOS 宏定义删除（第 28-36 行）

**现状代码（第 25-36 行）：**

```c
/******************local macroes*********************/
#define LOG_ROOT_DIR_WAIT_TIME  1000
#define LOG_ROOT_DIR_WAIT_COUNT 1
#ifndef LOS_WAIT_FOREVER
#define LOS_WAIT_FOREVER        0xFFFFFFFF
#endif
#ifndef LOS_NO_WAIT
#define LOS_NO_WAIT             0
#endif
#ifndef LOS_OK
#define LOS_OK                  0
#endif
```

**修改后：**

```c
/******************local macroes*********************/
#define LOG_ROOT_DIR_WAIT_TIME  1000
#define LOG_ROOT_DIR_WAIT_COUNT 1
```

**详细解释：**

- `LOS_WAIT_FOREVER`（0xFFFFFFFF）→ 直接用 CMSIS 标准常量 `osWaitForever`，其定义为 `0xFFFFFFFFU`（见 `cmsis_os2.h`），与原文**数值完全一致**，语义同为“无限等待”；
- `LOS_NO_WAIT`（0）→ 直接使用 `0U`，与 CMSIS `osSemaphoreAcquire` 的“不等待（轮询）”语义一致；
- `LOS_OK`（0）→ 直接用 CMSIS 标准枚举 `osOK`（值为 0）；
- `LOG_ROOT_DIR_WAIT_TIME` / `LOG_ROOT_DIR_WAIT_COUNT` 为本组件业务宏（等待日志根目录时长与次数），与内核接口无关，**保留不变**。

#### 4.1.3 修改点 3：信号量全局变量类型（第 47 行）

**现状代码（第 46-47 行）：**

```c
static UTILS_DL_LIST_HEAD(g_opsList);
static unsigned int g_opsListSem;
```

**修改后：**

```c
static UTILS_DL_LIST_HEAD(g_opsList);
static osSemaphoreId_t g_opsListSem = NULL;
```

**详细解释：**

- 原 `unsigned int` 保存的是 LiteOS 内核信号量句柄（`LOS_BinarySemCreate` 输出参数）；CMSIS 接口统一使用不透明句柄类型 `osSemaphoreId_t`（在 `cmsis_os2.h` 中定义为 `void *`，liteos_m 实现中实际指向内核信号量控制块 `LosSemCB`）；
- 初始化为 `NULL`：CMSIS 约定未创建成功的信号量 ID 为 NULL。`g_opsListSem` 在 `BBoxInit`（`CORE_INIT_PRI(..., 1)`）中创建，早于所有使用点（`BBoxRegisterModuleOps` 由 `BBoxAdapterInit` 在 `CORE_INIT_PRI(..., 2)` 中调用），初始化时序不受影响；
- 该变量为 `static`，仅本文件可见，类型变更无外部影响。

#### 4.1.4 修改点 4：`WaitForLogRootDir` 中延时接口（第 107 行）

**现状代码（第 97-110 行）：**

```c
static void WaitForLogRootDir(const char *rootDir)
{
    int i = 0;

    if (rootDir == NULL) {
        BBOX_PRINT_ERR("rootDir: %p\n", rootDir);
        return;
    }
    BBOX_PRINT_INFO("wait for log root dir [%s] begin!\n", rootDir);
    while (i++ < LOG_ROOT_DIR_WAIT_COUNT) {
        LOS_Msleep(LOG_ROOT_DIR_WAIT_TIME);
    }
    BBOX_PRINT_INFO("wait for log root dir [%s] end!\n", rootDir);
}
```

**修改后：**

```c
static void WaitForLogRootDir(const char *rootDir)
{
    int i = 0;

    if (rootDir == NULL) {
        BBOX_PRINT_ERR("rootDir: %p\n", rootDir);
        return;
    }
    BBOX_PRINT_INFO("wait for log root dir [%s] begin!\n", rootDir);
    while (i++ < LOG_ROOT_DIR_WAIT_COUNT) {
        (void)osDelay(LOG_ROOT_DIR_WAIT_TIME);
    }
    BBOX_PRINT_INFO("wait for log root dir [%s] end!\n", rootDir);
}
```

**详细解释：**

- `LOS_Msleep(1000)` 的入参单位是**毫秒**（内部按内核 tick 频率换算为 tick 后调用 `LOS_TaskDelay`）；
- `osDelay(1000)` 的入参单位是**系统 tick**。liteos_m 的 `osDelay` 实现：内核已启动时调用 `LOS_TaskDelay(ticks)`；内核未启动（`osKernelGetState() != osKernelRunning`）时执行 `HalDelay(ticks)` 忙等。`LOG_ROOT_DIR_WAIT_TIME`（1000）在 1000Hz（1 tick = 1 ms）的 mini 目标上与原行为完全等价；
- **必须核对目标内核 tick 频率**（`LOSCFG_BASE_CORE_TICK_PER_SECOND`）：内核默认值为 100Hz，`LOSCFG_BASE_CORE_TICK_PER_SECOND_MINI` 为 1000Hz，主流 mini 目标（如 ws63v100 为 1000Hz）均配置 1ms/tick。若目标配置非 1000Hz，需按 `osDelay(LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / 1000)` 换算，或将 `LOG_ROOT_DIR_WAIT_TIME` 按 tick 重新定义（详见第 5.1 节风险分析）；
- 返回值用 `(void)` 显式忽略：`osDelay` 返回 `osStatus_t`（ISR 中返回 `osErrorISR`），与本文件其他接口调用风格（`(void)LOS_SemPost(...)`）保持一致。

#### 4.1.5 修改点 5：`SaveErrorLog` 线程函数签名与信号量操作（第 143、158、161、185、188 行）

**现状代码（第 143-189 行）：**

```c
static void* SaveErrorLog(void *param)
{
    (void)param;
    struct ErrorInfo *info = NULL;
    struct BBoxOps *ops = NULL;
    char dirName[PATH_MAX_LEN] = { 0 };

    info = malloc(sizeof(*info));
    if (info == NULL) {
        BBOX_PRINT_ERR("malloc failed!\n");
        return NULL;
    }

    GetDirName(dirName, sizeof(dirName), GetFaultLogPath());
    WaitForLogRootDir(dirName);
    if (LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0) {
        BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
        free(info);
        return NULL;
    }
    ...
    (void)LOS_SemPost(g_opsListSem);
    free(info);

    return NULL;
}
```

**修改后（仅列出变更行，其余逻辑不动）：**

```c
static void SaveErrorLog(void *param)
{
    (void)param;
    struct ErrorInfo *info = NULL;
    struct BBoxOps *ops = NULL;
    char dirName[PATH_MAX_LEN] = { 0 };

    info = malloc(sizeof(*info));
    if (info == NULL) {
        BBOX_PRINT_ERR("malloc failed!\n");
        return;
    }

    GetDirName(dirName, sizeof(dirName), GetFaultLogPath());
    WaitForLogRootDir(dirName);
    if (osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK) {
        BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
        free(info);
        return;
    }
    ...
    (void)osSemaphoreRelease(g_opsListSem);
    free(info);

    return;
}
```

**详细解释：**

- **函数签名**：`osThreadFunc_t` 的标准定义是 `typedef void (*osThreadFunc_t)(void *argument);`，因此线程入口必须返回 `void`（原 `void*` 返回值仅 pthread 需要，改为 osThreadNew 后无意义）。函数体两处 `return NULL;` 相应改为 `return;`；
- **`LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0` → `osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK`**：
  - liteos_m 实现中 `osSemaphoreAcquire` 内部即调用 `LOS_SemPend`，等待语义完全一致；
  - 返回值：成功返回 `osOK`（0）；失败返回 `osErrorTimeout`（-2）/ `osErrorResource`（-3）/ `osErrorParameter`（-4）。原判断条件 `!= 0` 改为 `!= osOK`，语义等价且更符合 CMSIS 风格；
  - 无限等待使用 CMSIS 常量 `osWaitForever`（0xFFFFFFFFU），与原 `LOS_WAIT_FOREVER` 宏值一致；
- **`(void)LOS_SemPost(g_opsListSem)` → `(void)osSemaphoreRelease(g_opsListSem)`**：
  - liteos_m 实现中 `osSemaphoreRelease` 内部即调用 `LOS_SemPost`，行为一致；
  - 返回值差异：当信号量计数已达最大值时返回 `osErrorResource` 而非 `osOK`。此处为正常流程（先 Acquire 后 Release），计数不会溢出，返回值保持 `(void)` 忽略即可，与现状一致。

#### 4.1.6 修改点 6：`BBoxRegisterModuleOps` 中的信号量操作（第 224、235、244 行）

**现状代码（关键片段，第 222-244 行）：**

```c
    (void)memset_s(newOps, sizeof(*newOps), 0, sizeof(*newOps));
    (void)memcpy_s(&newOps->ops, sizeof(newOps->ops), ops, sizeof(*ops));
    if (LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0) {
        BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
        free(newOps);
        return -1;
    }
    if (UtilsListEmpty(&g_opsList)) {
        goto __out;
    }
    UTILS_DL_LIST_FOR_EACH_ENTRY(temp, &g_opsList, struct BBoxOps, opsList) {
        if (strcmp(temp->ops.module, ops->module) == 0) {
            BBOX_PRINT_ERR("[%s] has been registered!\n", ops->module);
            (void)LOS_SemPost(g_opsListSem);
            free(newOps);
            return -1;
        }
    }

__out:
    BBOX_PRINT_INFO("[%s] is registered successfully!\n", ops->module);
    UtilsListTailInsert(&g_opsList, &newOps->opsList);
    (void)LOS_SemPost(g_opsListSem);
```

**修改后（仅变更行）：**

```c
    (void)memset_s(newOps, sizeof(*newOps), 0, sizeof(*newOps));
    (void)memcpy_s(&newOps->ops, sizeof(newOps->ops), ops, sizeof(*ops));
    if (osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK) {
        BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
        free(newOps);
        return -1;
    }
    if (UtilsListEmpty(&g_opsList)) {
        goto __out;
    }
    UTILS_DL_LIST_FOR_EACH_ENTRY(temp, &g_opsList, struct BBoxOps, opsList) {
        if (strcmp(temp->ops.module, ops->module) == 0) {
            BBOX_PRINT_ERR("[%s] has been registered!\n", ops->module);
            (void)osSemaphoreRelease(g_opsListSem);
            free(newOps);
            return -1;
        }
    }

__out:
    BBOX_PRINT_INFO("[%s] is registered successfully!\n", ops->module);
    UtilsListTailInsert(&g_opsList, &newOps->opsList);
    (void)osSemaphoreRelease(g_opsListSem);
```

**详细解释：**

- 本函数用于注册故障模块的回调函数集合（`ModuleOps`），通过信号量保护 `g_opsList` 链表的并发访问。接口替换逻辑与 4.1.5 完全相同：
  - `LOS_SemPend(sem, LOS_WAIT_FOREVER)` → `osSemaphoreAcquire(sem, osWaitForever)`，返回值判断 `!= 0` → `!= osOK`；
  - 两处 `(void)LOS_SemPost(sem)` → `(void)osSemaphoreRelease(sem)`；
- 本函数运行于任务上下文（由 `BBoxAdapterInit` 的 `CORE_INIT_PRI` 初始化流程调用），`osWaitForever` 等待合法，无 ISR 约束问题；
- 错误路径（模块重复注册）保持“先 Release 再 free 再返回”的顺序不变，互斥保护逻辑与改造前完全一致。

#### 4.1.7 修改点 7：`BBoxNotifyError` 中的信号量操作（第 271、304 行）

**现状代码（关键片段，第 268-305 行）：**

```c
    GetDirName(dirName, sizeof(dirName), GetFaultLogPath());
    if (needSysReset == 0) {
        WaitForLogRootDir(dirName);
        if (LOS_SemPend(g_opsListSem, LOS_NO_WAIT) != 0) {
            BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
            goto __out;
        }
    }
    ...
    if (needSysReset == 0) {
        (void)LOS_SemPost(g_opsListSem);
    }
```

**修改后（仅变更行）：**

```c
    GetDirName(dirName, sizeof(dirName), GetFaultLogPath());
    if (needSysReset == 0) {
        WaitForLogRootDir(dirName);
        if (osSemaphoreAcquire(g_opsListSem, 0U) != osOK) {
            BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
            goto __out;
        }
    }
    ...
    if (needSysReset == 0) {
        (void)osSemaphoreRelease(g_opsListSem);
    }
```

**详细解释：**

- **`LOS_SemPend(g_opsListSem, LOS_NO_WAIT)` → `osSemaphoreAcquire(g_opsListSem, 0U)`**：`LOS_NO_WAIT` 宏值为 0，即“不等待、轮询获取”。CMSIS 中对应 timeout 为 `0U`，语义一致；
- **中断上下文安全性（本函数的关键约束）**：README 明确说明 `BBoxNotifyError` 可被放置在**故障中断上下文**中调用。liteos_m 的 `osSemaphoreAcquire` 实现中，当处于中断（`OS_INT_ACTIVE`）且 timeout 非 0 时直接返回 `osErrorParameter`，**仅 timeout = 0 允许在 ISR 中调用**。本处恰为 `0U` 轮询，替换后仍满足 ISR 安全约束，与改造前 `LOS_SemPend(sem, 0)` 的行为完全等价；
- **`(void)LOS_SemPost(...)` → `(void)osSemaphoreRelease(...)`**：liteos_m 的 `osSemaphoreRelease` 实现无 ISR 限制（内部 `LOS_SemPost` 本身中断安全），因此 `BBoxNotifyError` 从中断上下文调用时依然安全——这是 CMSIS-RTOS2 中少数允许 ISR 调用的接口之一，替换无风险；
- `needSysReset != 0`（需要立即重启）分支原本就不加锁（直接 Dump/Reset/Reboot），结构保持不变。

#### 4.1.8 修改点 8：`BBoxInit` 中信号量创建（第 321、323 行）

**现状代码（第 318-327 行）：**

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
    ...
```

**修改后：**

```c
static void BBoxInit(void)
{
    if (osSemaphoreNew(1, 1, NULL) == NULL) {
        BBOX_PRINT_ERR("Create binary semaphore failed!\n");
        return;
    }
    UtilsListInit(&g_opsList);
    ...
```

**注意**：第 321 行的局部变量 `int ret = -1;` 与 `pthread_t taskId = 0;` 需要结合修改点 9 一并处理（`ret` 原用于接收 `pthread_create` 返回值，`taskId` 原为 pthread 线程 ID，两者在修改点 9 完成后一并删除），完整合并后的函数见 4.1.9。

**详细解释：**

- **`LOS_BinarySemCreate(1, &g_opsListSem) != LOS_OK` → `osSemaphoreNew(1, 1, NULL) == NULL`**：
  - `osSemaphoreNew` 参数含义：`max_count`（最大计数）= 1、`initial_count`（初始计数）= 1、`attr` = NULL（使用默认属性，liteos_m 实现中忽略该参数）；
  - **实现层完全等价**：liteos_m 的 `osSemaphoreNew` 实现中，当 `max_count == 1` 时内部直接调用 `LOS_BinarySemCreate(initial_count, &semId)`——即与原代码调用的内核接口完全相同，二进制信号量语义（计数上限 1、初始 1）零差异；
  - 失败判定：`osSemaphoreNew` 失败返回 NULL（原接口失败返回非 `LOS_OK`），判定式相应从 `!= LOS_OK` 改为 `== NULL`；
  - 调用时机：`BBoxInit` 通过 `CORE_INIT_PRI(BBoxInit, 1)` 在内核初始化任务上下文中执行，`osSemaphoreNew` 不允许在 ISR 调用（ISR 中返回 NULL），此处为任务上下文，合法；
  - 失败处理保持原逻辑：创建失败直接 return（后续 `BBoxAdapterInit` 注册时 Acquire 会因句柄为 NULL 返回 `osErrorParameter`，注册失败打印错误日志，防御路径与现状一致）。

#### 4.1.9 修改点 9：`BBoxInit` 中线程创建（第 321、328-331 行）

**现状代码（第 318-333 行，含修改点 8 上下文）：**

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

**修改后（修改点 8 + 9 合并结果）：**

```c
static void BBoxInit(void)
{
    osThreadAttr_t taskAttr = { 0 };

    if (osSemaphoreNew(1, 1, NULL) == NULL) {
        BBOX_PRINT_ERR("Create binary semaphore failed!\n");
        return;
    }
    UtilsListInit(&g_opsList);
    taskAttr.name = "BlackBoxTask";
    taskAttr.priority = osPriorityNormal;
    taskAttr.stack_size = BLACKBOX_TASK_STACK_SIZE;
    if (osThreadNew(SaveErrorLog, NULL, &taskAttr) == NULL) {
        BBOX_PRINT_ERR("Falied to create SaveErrorLog task!\n");
    }
}
CORE_INIT_PRI(BBoxInit, 1);
```

**详细解释：**

- **`pthread_create(&taskId, NULL, SaveErrorLog, NULL)` → `osThreadNew(SaveErrorLog, NULL, &taskAttr)`**：
  - `osThreadNew` 三个参数：线程入口函数 `func`（须为 `void (*)(void *)`，即修改点 5 调整后的 `SaveErrorLog` 签名）、入口参数 `argument`（原为 NULL，保持 NULL）、线程属性 `attr`；
  - 返回值：成功返回 `osThreadId_t`（非 NULL），失败返回 NULL，判定式由 `ret != 0` 改为 `== NULL`；原错误打印中的 `ret: %d` 不再有对应错误码，相应简化错误信息；
  - 原局部变量 `int ret`、`pthread_t taskId` 一并删除（`taskId` 创建后从未使用，`ret` 仅用于错误打印）；
- **线程属性显式指定（本方案重点，见第 5.2 节风险分析）**：
  - 原 `pthread_create` 传 NULL 属性时，liteos_m 的 musl porting 在 `pthread_attr_init` 中将默认栈大小设为 **`0x2000`（8KB）**、优先级 25；
  - 而 `osThreadNew` 传 NULL 属性时，liteos_m 实现使用 `LOSCFG_BASE_CORE_TSK_DEFAULT_STACK_SIZE`（内核默认 **`0x400`，仅 1KB**）——**若直接传 NULL，线程栈从 8KB 缩水到 1KB**；
  - `SaveErrorLog` 栈上局部变量有 `char dirName[PATH_MAX_LEN]`（256 字节），且会调用 `FullWriteFile` 等平台文件接口（hi3861 等 flash 文件系统实现栈开销较大），1KB 栈存在溢出风险。因此**必须显式指定 `stack_size = 0x2000`**（与改造前 pthread 默认栈一致，行为保真），并通过文件顶部新增宏定义，例如：

    ```c
    #define BLACKBOX_TASK_STACK_SIZE  0x2000
    ```

  - `name` 指定为 `"BlackBoxTask"`：原 pthread 线程由 musl 命名为 `pthread` 类默认名，CMSIS 默认名为 `"CmsisTask"`，显式命名便于内核 shell（如 `task` 命令）排障时识别，属可选优化；
  - `priority = osPriorityNormal`（CMSIS 标准值 24）：原 pthread 默认优先级 25（SCHED_RR）。二者经 liteos_m 优先级换算后相近且本线程为低频后台日志保存任务，无实时性要求，`osPriorityNormal` 可满足需求；如需与内核优先级严格对齐，可在 `osThreadAttr_t` 中进一步精确指定；
- **调用时机合法性**：`osThreadNew` 不允许在 ISR 中调用（liteos_m 实现在 `OS_INT_ACTIVE` 时返回 NULL）。`BBoxInit` 运行于内核初始化任务上下文，合法；
- `CORE_INIT_PRI(BBoxInit, 1)` 保持不动：信号量与线程仍在内核启动早期（PRI 1）创建，早于 `BBoxAdapterInit`（PRI 2）的模块注册，时序不变。

#### 4.1.10 修改后 `blackbox_core.c` 完整变更汇总

| 行号（现状） | 变更内容 |
| --- | --- |
| 21 | `#include "pthread.h"` → `#include "cmsis_os2.h"` |
| 26-27 之后 | 新增宏 `#define BLACKBOX_TASK_STACK_SIZE 0x2000`（用于 osThreadNew 显式栈） |
| 28-36 | 删除 `LOS_WAIT_FOREVER` / `LOS_NO_WAIT` / `LOS_OK` 三个本地宏 |
| 47 | `static unsigned int g_opsListSem;` → `static osSemaphoreId_t g_opsListSem = NULL;` |
| 107 | `LOS_Msleep(LOG_ROOT_DIR_WAIT_TIME);` → `(void)osDelay(LOG_ROOT_DIR_WAIT_TIME);` |
| 143 | `static void* SaveErrorLog(void *param)` → `static void SaveErrorLog(void *param)` |
| 158 | `LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0` → `osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK` |
| 161, 188 | `return NULL;` → `return;`（SaveErrorLog 内两处） |
| 185 | `(void)LOS_SemPost(g_opsListSem);` → `(void)osSemaphoreRelease(g_opsListSem);` |
| 224 | `LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0` → `osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK` |
| 235, 244 | `(void)LOS_SemPost(g_opsListSem);` → `(void)osSemaphoreRelease(g_opsListSem);` |
| 271 | `LOS_SemPend(g_opsListSem, LOS_NO_WAIT) != 0` → `osSemaphoreAcquire(g_opsListSem, 0U) != osOK` |
| 304 | `(void)LOS_SemPost(g_opsListSem);` → `(void)osSemaphoreRelease(g_opsListSem);` |
| 321 | 删除 `int ret = -1;` 与 `pthread_t taskId = 0;`，改为 `osThreadAttr_t taskAttr = { 0 };` |
| 323 | `LOS_BinarySemCreate(1, &g_opsListSem) != LOS_OK` → `osSemaphoreNew(1, 1, NULL) == NULL` |
| 328-331 | `pthread_create(&taskId, NULL, SaveErrorLog, NULL)` + `ret != 0` 判断 → `osThreadNew(SaveErrorLog, NULL, &taskAttr) == NULL` 判断（含 taskAttr 字段赋值） |

### 4.2 `interfaces/native/kits/blackbox_adapter.h`（修改点 11）

**现状代码（第 41-44 行）：**

```c
/* The following functions have been implemented in the kernel */
extern unsigned int LOS_BinarySemCreate(unsigned short count, unsigned int *semHandle);
extern unsigned int LOS_SemPend(unsigned int semHandle, unsigned int timeout);
extern unsigned int LOS_SemPost(unsigned int semHandle);
```

**修改后：整段删除（连同注释）。**

**详细解释：**

- 这三行是对 LiteOS 内核原生信号量接口的 `extern` 声明，注释标明“已由内核实现”。经核实，本仓所有 .c 文件（`blackbox_core.c` / `blackbox_adapter.c` / `blackbox_detector.c`）均未引用这三个声明——它们属于历史残留，实际信号量调用由内核头文件直接提供声明；
- 适配目标即“消除 LOS_ 接口使用”，该残留声明属于清理范围，直接删除；
- **对外影响核查**：全工作区检索 `blackbox_adapter.h` 的引用方，唯一外部使用者为 `device/soc/hisilicon/hi3861v100/sdk_liteos/app/wifiiot_app/src/blackbox_adapter_impl.c`，该文件实际包含的是设备侧自有的 `hi_blackbox_adapter.h`，与本仓头文件无关；且其实现代码不含任何 LOS/pthread 调用。故删除不会破坏任何现有构建或设备侧适配实现。

### 4.3 `interfaces/native/innerkits/blackbox_adapter.h`（修改点 12）

**现状代码（第 41-44 行）：** 与 4.2 节完全一致（两份头文件内容相同）。

**修改后：** 同 4.2 节，整段删除。

**详细解释：**

- innerkits 与 kits 两份头文件为内容完全相同的双份拷贝（维护策略如此，本次适配仅清理残留声明，不改变双份结构）；
- 删除理由与对外影响核查同 4.2 节，两处必须**同步修改**以保持一致性。

### 4.4 `BUILD.gn`（潜在兜底，默认不改）

**现状：** 源码列表 `blackbox_adapter.c` / `blackbox_core.c` / `blackbox_detector.c` 不变（无新增文件）；`include_dirs` 不变。

**条件性修改（仅当编译报 `cmsis_os2.h: No such file or directory` 时执行）：**

```gn
  include_dirs = [
    "//base/hiviewdfx/blackbox_lite",
    "//base/hiviewdfx/blackbox_lite/interfaces/native/kits",
    "//base/hiviewdfx/hiview_lite",
    "//base/hiviewdfx/hilog_lite/interfaces/native/kits/hilog_lite",
    "//commonlibrary/utils_lite/include",
    "//kernel/liteos_m/kal/cmsis",   # 兜底：CMSIS-RTOS2 头文件路径
  ]
```

**详细解释：**

- 正常情况下无需修改：`cmsis_os2.h` 由 liteos_m 内核 CMSIS KAL 模块（`kernel/liteos_m/kal/cmsis`）的 public config 提供 include 路径，`blackbox_lite` 已在 `bundle.json` 依赖 `liteos_m`，mini 目标默认开启 `LOSCFG_KAL_CMSIS`；
- 若某些目标的内核配置未传播该 public config，按上述方式追加 include 目录即可，链接阶段 CMSIS 符号（`osSemaphoreNew` 等）由内核 KAL 实现提供，无需新增链接依赖。

### 4.5 `bundle.json`（不改）

`adapted_system_type: ["mini"]`、`deps`（`utils_lite` / `liteos_m`）均保持不变：

- `liteos_m` 继续提供 CMSIS-RTOS2 运行时与头文件；
- `utils_lite` 继续提供 `utils_list.h` 链表能力，与本适配无关。

### 4.6 `README_zh.md` / `OAT.xml`（不改）

- README 中未出现 LOS/pthread 接口描述，仅提及“SaveErrorLog 线程”这一业务概念，适配后依然成立，无需更新；
- OAT.xml 仅约束开源许可证审查范围，本次无新增文件、无新增第三方依赖，无需更新。

---

## 5. 关键语义差异与风险分析

### 5.1 `osDelay` 单位为 tick（毫秒 vs tick 换算）

- `LOS_Msleep` 入参单位为毫秒（内部按 `LOSCFG_BASE_CORE_TICK_PER_SECOND` 换算为 tick）；
- `osDelay` 入参单位为 tick。liteos_m 内核默认 tick 频率为 **100Hz**（`los_config.h` 中 `LOSCFG_BASE_CORE_TICK_PER_SECOND` 默认 100），`LOSCFG_BASE_CORE_TICK_PER_SECOND_MINI` 为 1000Hz；主流 mini 目标（ws63v100 等）实际配置为 **1000Hz**，即 1 tick = 1ms，此时 `osDelay(1000)` 与原 `LOS_Msleep(1000)` 行为完全等价；
- **适配时必须核对目标设备的 `LOSCFG_BASE_CORE_TICK_PER_SECOND` 配置**：若为 100Hz（1 tick = 10ms），直接替换将导致等待时间从 1s 变为 10s，需按 `osDelay(LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / 1000)` 换算；
- 附加差异：内核未启动时 `osDelay` 走 `HalDelay` 忙等路径，`LOS_Msleep` 无此分支，但 `WaitForLogRootDir` 的调用时机均在系统初始化之后（`BBoxNotifyError` / `SaveErrorLog` 运行时），不受影响。

### 5.2 线程栈大小差异（本次适配最重要的行为保真点）

| 创建方式 | 默认栈大小 | 优先级 |
| --- | --- | --- |
| 原 `pthread_create(..., NULL, ...)`（musl liteos_m porting） | `0x2000`（8KB，`pthread_attr_init` 设定） | 25 |
| `osThreadNew(..., NULL)`（liteos_m CMSIS 实现） | `LOSCFG_BASE_CORE_TSK_DEFAULT_STACK_SIZE`，默认 `0x400`（1KB） | `osPriorityNormal`（24） |

- 若直接以 NULL 属性调用 `osThreadNew`，`SaveErrorLog` 线程栈从 8KB 缩小到 1KB；该函数栈上含 `char dirName[PATH_MAX_LEN]`（256B）并调用平台文件接口，**存在栈溢出风险**；
- 因此方案中（4.1.9）显式指定 `osThreadAttr_t`，`stack_size = 0x2000` 与原行为保真，并显式命名线程、指定优先级，便于定位排障。

### 5.3 中断上下文约束（`BBoxNotifyError` 可从 ISR 调用）

| 接口 | ISR 可调用性（liteos_m 实现） | 本仓使用场景 |
| --- | --- | --- |
| `osSemaphoreAcquire(sem, 0U)` | 允许（timeout 必须为 0） | `BBoxNotifyError` 的 `needSysReset==0` 路径，原 `LOS_SemPend(sem, 0)` 同样 ISR 安全，**等价** |
| `osSemaphoreAcquire(sem, osWaitForever)` | 禁止（ISR 中返回 `osErrorParameter`） | 仅 `SaveErrorLog` / `BBoxRegisterModuleOps` 任务上下文使用，**合法** |
| `osSemaphoreRelease` | 允许（无 ISR 检查） | `BBoxNotifyError` 可能从 ISR 调用，**安全** |
| `osDelay` | 禁止（ISR 中返回 `osErrorISR`，即不等待） | `WaitForLogRootDir` 可能经 `BBoxNotifyError` 从 ISR 调用；原 `LOS_Msleep` 在 ISR 中同样不产生任务级延时，属**既有行为**，适配不引入回归，但建议知悉 |
| `osThreadNew` | 禁止（ISR 中返回 NULL） | `BBoxInit` 任务上下文调用，**合法** |

### 5.4 返回值语义差异

- `osStatus_t` 为枚举：`osOK = 0`、`osError = -1`、`osErrorTimeout = -2`、`osErrorResource = -3`、`osErrorParameter = -4`、`osErrorISR = -6`；
- 原代码以 `!= 0` 判定 `LOS_SemPend` 失败，改为 `!= osOK` 后语义等价（`osOK == 0`）且更清晰；
- `osSemaphoreRelease` 在计数已满时返回 `osErrorResource`（原 `LOS_SemPost` 同样返回错误码），本仓所有 Post/Release 调用点均为 `(void)` 忽略返回值，无差异；
- `osSemaphoreNew` 失败返回 NULL（原返回非 `LOS_OK`），判定式 `== NULL` 已按 CMSIS 惯例改写。

### 5.5 初始化时序

- `CORE_INIT_PRI(BBoxInit, 1)`：创建信号量 + 创建线程（内核初始化任务上下文，CMSIS 接口合法）；
- `CORE_INIT_PRI(BBoxAdapterInit, 2)`：注册 SYSTEM 模块 ops（需信号量已就绪）；
- 替换后的接口调用时机与依赖关系与原实现完全一致，无时序风险。

---

## 6. 验证方案

### 6.1 静态残留检查

```bash
cd base/hiviewdfx/blackbox_lite
grep -rn "LOS_\|pthread" --include="*.c" --include="*.h" .
```

期望结果：**0 命中**（含 `interfaces/native/kits` 与 `interfaces/native/innerkits` 两份头文件）。

### 6.2 编译验证

1. 选择 mini 目标整包构建（推荐 `hispark_pegasus`/Hi3861，即 README 引用的适配平台），或先做单组件编译：

   ```bash
   hb build -T //base/hiviewdfx/blackbox_lite:blackbox_lite
   ```

2. 重点确认：
   - `cmsis_os2.h` 可解析（否则按 4.4 节追加 include 路径）；
   - 链接无未定义符号（`osSemaphoreNew` / `osSemaphoreAcquire` / `osSemaphoreRelease` / `osDelay` / `osThreadNew` 均由内核 CMSIS KAL 提供，mini 目标默认具备）；
   - 编译告警零新增（`-Wall` 开启：确认 `taskAttr` 无未使用字段告警、无隐式类型转换告警）。

### 6.3 功能验证用例

| 用例 | 步骤 | 预期 |
| --- | --- | --- |
| 启动初始化 | 设备上电，观察启动日志 | `BBoxInit` 创建信号量与线程成功，无 "Create binary semaphore failed"、无 "Falied to create SaveErrorLog task"；`task` 命令可见 `BlackBoxTask` 线程 |
| 模块注册 | `BBoxAdapterInit` 注册 SYSTEM 模块 | 打印 "[SYSTEM] is registered successfully!" |
| SaveErrorLog 执行 | 开机后线程运行 | 无栈溢出（无异常复位）、`WaitForLogRootDir` 等待时长与改造前一致（约 1s，用于核对 tick 频率） |
| BBoxNotifyError（不重启） | 任务上下文调用 `BBoxNotifyError(..., needSysReset=0)` | 正常执行 Dump/Reset 或 SaveBasicErrorInfo 流程，信号量轮询获取与释放正常 |
| BBoxNotifyError（不重启，ISR 场景） | 从中断/异常上下文调用 `BBoxNotifyError(..., needSysReset=0)` | `osSemaphoreAcquire(sem, 0U)` 轮询合法，不发生非法上下文调用 |
| BBoxNotifyError（重启） | `needSysReset=1` 调用 | 跳过信号量操作，Dump/Reset 后 `RebootSystem` 正常触发重启 |
| 并发压力 | 反复注册/通知/线程保存流程 | 链表在信号量保护下无并发异常 |

---

## 7. 实施步骤与顺序

| 步骤 | 内容 | 涉及文件 |
| --- | --- | --- |
| 1 | 修改 `blackbox_core.c`：头文件、宏、变量类型、全部 10 个修改点 | `blackbox_core.c` |
| 2 | 删除两份头文件中的 LOS 残留声明 | `interfaces/native/kits/blackbox_adapter.h`、`interfaces/native/innerkits/blackbox_adapter.h` |
| 3 | 静态残留检查（6.1） | - |
| 4 | 编译验证（6.2），必要时补 `BUILD.gn` include 兜底 | `BUILD.gn`（条件性） |
| 5 | 核对目标 tick 频率配置，确认 `osDelay` 换算（5.1） | - |
| 6 | 板级功能验证（6.3） | - |
| 7 | 提交评审（PR 描述附本方案文档） | - |

---

## 8. 附录：涉及文件与改动统计

| 文件 | 改动性质 | 修改点数量 |
| --- | --- | --- |
| `blackbox_core.c` | 接口替换 + 头文件 + 宏 + 变量类型 + 线程函数签名 | 10 |
| `interfaces/native/kits/blackbox_adapter.h` | 删除残留声明 | 1 |
| `interfaces/native/innerkits/blackbox_adapter.h` | 删除残留声明 | 1 |
| `BUILD.gn` | 默认不改（条件性兜底） | 0~1 |
| `bundle.json` / `README_zh.md` / `OAT.xml` | 不改 | 0 |

**接口映射合规性核对**（对照需求统一动作）：

| 需求统一动作 | 本方案落实 |
| --- | --- |
| `LOS_Sem*` → `osSemaphore*` | ✅ `LOS_BinarySemCreate`→`osSemaphoreNew`、`LOS_SemPend`→`osSemaphoreAcquire`、`LOS_SemPost`→`osSemaphoreRelease`（共 10 处调用 + 2 处残留声明删除） |
| `LOS_Msleep` → `osDelay` | ✅ 1 处（`WaitForLogRootDir`），并附 tick 频率核查要求 |
| `pthread_create` → `osThreadNew` | ✅ 1 处（`BBoxInit`），显式线程属性保真原 8KB 栈行为 |
| mini 组件使用 CMSIS | ✅ 本组件为纯 mini 组件，全仓 CMSIS-RTOS2，无 POSIX 分支、无分支隔离 |
