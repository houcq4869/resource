# blackbox_lite 组件代码详解与评审讲解手册

> 面向对象：刚接触 OpenHarmony 的开发者（无需提前了解 LiteOS 或 CMSIS）
> 用途：评审会讲解前自学 + 讲解参考
> 对应代码仓：`base/hiviewdfx/blackbox_lite`（OpenHarmony 轻量系统黑盒组件）

---

# 第一部分 基础概念篇

## 1. 黑盒（blackbox）组件是什么

### 1.1 从飞机黑匣子说起

飞机出事之后，调查人员做的第一件事是找**黑匣子**——它忠实地记录了坠机前最后一刻
飞机的姿态、速度、驾驶舱声音。有了它，才能还原"最后一刻发生了什么"。

OpenHarmony 的黑盒组件（blackbox）在软件世界里干的是同一件事：

> **当系统或某个模块发生致命错误（panic、看门狗复位、掉电、系统重启）时，
> 在"倒下"之前，把各个模块的关键现场信息（错误事件、模块名、错误描述、各模块自带的诊断数据）
> 收集、保存下来，供事后分析定位问题。**

### 1.2 典型使用场景

| 场景 | 黑盒做什么 |
|---|---|
| 内核 panic / 系统看门狗复位 | 复位前把各模块的关键寄存器、状态信息 dump 到日志文件 |
| 掉电 / 异常关机 | 保存"最后发生了什么"的痕迹 |
| 某个业务模块检测到自身异常 | 调用黑盒接口记录事件，按需触发模块自检（Dump）或重启（Reset） |

### 1.3 一句话定义

> **blackbox_lite 是 OpenHarmony 轻量系统（mini 系统）的"软件故障现场记录器"：
> 各模块向它注册自己的"诊断回调"，出错时它负责分发通知、收集现场、保存日志。**

**一句话小结**：黑盒 = 故障现场记录器；核心价值 = 出事之后能知道"最后一刻发生了什么"。

---

## 2. 嵌入式 RTOS 最小概念集（零基础必读）

黑盒组件用到了信号量、线程、延时等 RTOS（实时操作系统）机制。下面用生活类比把
**本组件涉及的全部概念**一次讲清。理解了这一章，后面看代码会非常顺。

### 2.1 任务 / 线程

- **一句话**：任务是操作系统中"独立运行的一段代码"，CPU 在多个任务之间快速切换，看起来像同时执行。
- **类比**：一个餐厅只有一个服务员（单核 CPU），但他同时在接待三桌客人——给 A 桌点完菜，
  跑去给 B 桌上菜，再给 C 桌结账。每桌客人的需求就是"任务"，服务员的快速切换就是"调度"。
- **本组件中的任务**：`SaveErrorLog` 是一个后台线程，专门负责"等通知、收集日志、保存"。

### 2.2 信号量（Semaphore）

- **一句话**：信号量是一种"计数令牌"，任务**拿**（P 操作）到令牌才能进入受保护的资源，
  用完必须**还**（V 操作）回去。
- **类比**：停车场只有 1 个车位（**二元信号量**）。车来了，如果车位空着就拿"车位令牌"停进去；
  如果车位被占（令牌没了）就**等**（阻塞）或**直接走**（非阻塞）；车开走时必须还令牌。
- **关键区分**：
  - **阻塞等待**：拿不到就一直等（`osWaitForever`）
  - **非阻塞等待**：拿不到立刻返回失败（超时时间 = 0）
- **为什么需要它**：保护"共享资源"。黑盒里的共享资源是**模块注册链表**——
  多个任务（注册者、通知者、保存线程）可能同时访问它，必须保证同一时刻只有一个人进去改。
  这种"同一时刻只允许一个人进入的区域"叫**临界区**。
- **P/V 命名**：P 来自荷兰语 Proberen（尝试/获取），V 来自 Verhogen（增加/释放）。
  代码里 P 操作 = Pend/Acquire，V 操作 = Post/Release。

### 2.3 tick（时钟节拍）

- **一句话**：tick 是操作系统的心跳，内核按固定频率"跳"，每次心跳叫 1 tick。
- **tick 频率**：WS63 内核为 **1000Hz**，即 1 tick = 1ms（一秒钟跳 1000 次）。
  有的产品是 100Hz（1 tick = 10ms）。
- **重要坑（本次改造的核心知识点）**：有些延时接口按 **毫秒** 计时，有些按 **tick 数** 计时！
  同样想延时 1 秒：毫秒接口传 `1000`；tick 接口在 1000Hz 系统上传 `1000`、在 100Hz 系统上传 `100`。
  传错了会差 10 倍时间。**CMSIS 的 osDelay 就是按 tick 计时的**——这就是改造时必须做换算的原因（详见 14.5）。

### 2.4 句柄（handle）

- **一句话**：句柄是操作系统发给你的"取号小票"，拿着它就能操作对应的内核对象，
  但你看不到也不直接碰对象本体。
- **类比**：银行办业务，柜台给你一张号码小票。之后叫号、办业务都凭这张票。
  你不直接站到柜台里面去，票丢了就办不了。
- **本组件中**：信号量创建后返回一个句柄 `g_opsListSem`，之后的 P/V 操作都凭它。

### 2.5 弱符号（WEAK）与 CORE_INIT 启动注册

- **弱符号**：`__attribute__((weak))` 修饰的函数叫弱符号函数——"我先给个默认实现，
  谁都可以用自己的实现把我覆盖掉（覆写），不覆写就用我的默认版"。
  - **类比**：酒店给每个房间配了默认的白床单（弱实现）；客人可以自带宽床单换上（强实现覆盖）。
- **本组件中**：7 个"平台适配接口"（写文件、获取路径、重启系统等）都是弱符号——
  黑盒只负责逻辑，具体怎么落盘由每个平台自己实现；平台没实现就打印一行
  `Please implement the interface according to the platform!`。
- **CORE_INIT**：OpenHarmony 轻量系统的启动注册机制。函数用 `CORE_INIT_PRI(func, 优先级)` 注册后，
  系统启动时会**按优先级从小到大自动调用**这些函数，无需手动写调用代码。
  - **类比**：开学典礼的程序单。`CORE_INIT_PRI(A, 1)` 就是"A 在典礼第 1 项上台"。

### 2.6 双向链表（utils_list）

- **一句话**：一种"每个节点都记住前一个和后一个伙伴"的数据结构，适合"动态增删查"。
- **类比**：小朋友手拉手排成一圈，每人左手拉前面的人、右手拉后面的人。
  新同学随时可以插进圈里，走掉也不会断圈。
- **本组件中**：模块注册表 `g_opsList` 就是一个双向链表，每个节点是一个"已注册模块"。
  查重、尾插都靠它。

**一句话小结**：本章 6 个概念（任务、信号量、tick、句柄、弱符号/CORE_INIT、链表）
覆盖了 blackbox 组件用到的全部基础机制，后文遇到时请回看本章。

---

## 3. 三个接口体系：LiteOS、CMSIS-RTOS2、POSIX

### 3.1 LiteOS 与 LOS_ 接口

- **LiteOS**：OpenHarmony 自研的轻量级操作系统内核（liteos_m / liteos_a）。
- **LOS_ 接口**：LiteOS 内核提供给应用程序的 C 函数，名字统一以 `LOS_` 开头，
  如 `LOS_SemPend`（等信号量）、`LOS_Msleep`（毫秒延时）。这些接口是 **LiteOS 私有（专有）的**——
  换一个内核（比如 FreeRTOS、Zephyr）这些函数就不存在了。

### 3.2 CMSIS 与 CMSIS-RTOS2

- **CMSIS**（Cortex Microcontroller Software Interface Standard）：ARM 公司发布的
  Cortex 微控制器软件接口标准，核心思想是"**硬件和内核可以换，但软件接口长一样**"。
- **CMSIS-RTOS2**：CMSIS 标准里的"RTOS 通用 API 规范"（RTOS2 是第二版）。它只规定
  "接口应该长什么样"（比如 `osDelay(ticks)`），**不规定谁来实现**——LiteOS、FreeRTOS、Zephyr
  都可以在下面提供一套符合规范的实现。
  - **类比**：USB-C 接口标准。手机、充电器谁造的都可以，只要接口符合 USB-C 规范就能插上。
- **本组件改造后**：只调用 `osSemaphore*`/`osDelay`/`osThreadNew` 这些 CMSIS-RTOS2 标准接口，
  下面不管是 LiteOS 内核还是别的内核，只要提供了 RTOS2 实现，黑盒代码一行不用改。

### 3.3 POSIX / pthread

- **POSIX**：UNIX 系操作系统（Linux 等）的标准接口族；`pthread_create` 是其中"创建线程"的标准接口。
- **本组件改造前**混用了 pthread（建线程）与 LOS_（信号量/延时）；**改造后**按专项要求
  全部统一到 CMSIS-RTOS2（本组件是 mini 系统组件，专项规定 mini 用 CMSIS、small 用 POSIX）。

### 3.4 为什么要做这次改造

| 改造前 | 问题 | 改造后 |
|---|---|---|
| `LOS_SemPend` 等私有接口 | 绑定 LiteOS 内核，换内核必须改源码；各组件各自为政 | `osSemaphoreAcquire` 标准接口 |
| 私有接口 + POSIX 混用 | 风格不统一，可移植性差 | 统一 CMSIS-RTOS2 |
| 公开头里复制内核声明 | API 污染 | 公开头只保留组件自己的接口 |

> **改造动机一句话**：把"绑死一家内核的私有接口"换成"跨内核的标准接口"，
> 让组件代码与内核解耦，可移植、可复用。

**一句话小结**：LOS_ 是 LiteOS 私有接口；CMSIS-RTOS2 是 ARM 的跨内核标准 API 规范；
专项要求 mini 组件统一用 CMSIS——本次改造就是做这件事。

---

# 第二部分 组件功能与整体逻辑篇

## 4. 组件功能全景：三件套

blackbox_lite 的全部逻辑可以概括为"**三件套**"：

```
                          ┌─────────────────────────────────────────┐
                          │            blackbox_lite（黑盒）         │
                          │                                         │
  ① 各业务模块 ──注册──▶  │  ① 注册表 g_opsList（双向链表）          │
     （wifi/安全/…）       │      每个节点：模块名 + 4 个诊断回调     │
                          │                                         │
  ② 错误发生者 ──通知──▶  │  ② 通知分发 BBoxNotifyError              │
     （任何代码）          │      按模块名找到节点 → 调用它的回调      │
                          │                                         │
                          │  ③ 后台保存线程 SaveErrorLog              │
                          │      阻塞等锁 → 遍历所有模块保存日志      │
                          └──────────────┬──────────────────────────┘
                                         │ 信号量 g_opsListSem 保护注册表
                                         ▼
                              平台适配层（7 个弱符号接口：写文件/取路径/重启…）
```

- **① 注册表**：谁想被黑盒"照顾"，谁先来登记（登记时带上自己的诊断回调函数）。
- **② 通知分发**：出错了，喊一声 `BBoxNotifyError(事件, 模块名, 描述, 是否复位)`，
  黑盒找到对应模块，调用它登记时留下的回调（Dump = 现场转储，Reset = 复位前处理）。
- **③ 后台保存线程**：一个常驻后台的任务，专门把各模块保存的日志收走上传。
- **锁**：三件套都访问同一个注册表，所以用**一个二元信号量**做互斥。

## 5. 仓库文件地图

| 文件 | 职责一句话 |
|---|---|
| `blackbox_core.c` | **核心逻辑**：注册表、通知分发、后台保存线程（本次改造唯一动逻辑的文件） |
| `blackbox_adapter.c` | 平台适配层：7 个弱符号接口的默认实现 + 启动时注册 SYSTEM 模块 |
| `blackbox_detector.c/.h` | 事件上传桩（预留接口，空实现） |
| `interfaces/native/kits/blackbox.h` | 对外 API 声明 + 数据结构（ErrorInfo/ModuleOps） |
| `interfaces/native/kits/blackbox_adapter.h` | 平台适配接口声明（改造后已无 LOS 声明） |
| `interfaces/native/innerkits/...`（两份） | 与 kits 内容一致的副本，同步维护 |
| `BUILD.gn` | 构建脚本（静态库 blackbox_lite；本次加 CMSIS 头文件路径） |
| `bundle.json` | 组件元数据（本次补第三方依赖 cmsis） |
| `README_zh.md / LICENSE / OAT.xml / figures/` | 文档与合规材料，不涉及代码 |

## 6. 数据结构逐字段讲解

### 6.1 `struct ErrorInfo`（blackbox.h:50-54）——一条错误记录

```c
struct ErrorInfo {
    char event[EVENT_MAX_LEN];      // 32 字节：事件名，如 "PANIC"、"SYSWATCHDOG"
    char module[MODULE_MAX_LEN];    // 32 字节：模块名，如 "SYSTEM"、"WIFI"
    char errorDesc[ERROR_DESC_MAX_LEN]; // 512 字节：错误描述文本
};
```
类比：一张"事故报告单"——事发事件、发生在哪个模块、详细描述。

### 6.2 `struct ModuleOps`（blackbox.h:56-62）——一个模块的"诊断能力"登记表

```c
struct ModuleOps {
    char module[MODULE_MAX_LEN];        // 模块名（注册表的查重依据）
    void (*Dump)(const char *logDir, struct ErrorInfo *info);      // 现场转储回调
    void (*Reset)(struct ErrorInfo *info);                          // 复位前处理回调
    int (*GetLastLogInfo)(struct ErrorInfo *info);                  // 取最后日志信息
    int (*SaveLastLog)(const char *logDir, struct ErrorInfo *info); // 保存最后日志
};
```
模块登记时填这张表：**我叫什么、出事时你怎么帮我转储现场、复位前你要做什么、
怎么取/存我的日志**。4 个回调都可以是 NULL（不填 = 不提供该能力）。

### 6.3 `struct BBoxOps`（blackbox_core.c:31-34）——注册表的节点

```c
struct BBoxOps {
    UTILS_DL_LIST opsList;   // 链表节点（前驱/后继指针），用于挂到注册表上
    struct ModuleOps ops;    // 上面那张登记表
};
```
内存布局示意：

```
g_opsList（链表头）
  │
  ▼
[节点A] opsList(前后指针) + ops{module="SYSTEM",  Dump=..., Reset=..., ...}
  │ next
  ▼
[节点B] opsList(前后指针) + ops{module="WIFI", ...}
  │ next
  ▼
（绕回链表头，环形双向链表）
```

## 7. 启动时序（时间线叙事）

```
上电复位
  │
  ▼
LOS_KernelInit()            ← 内核自身初始化（内存、任务管理就绪，但调度器还没转起来）
  │
  ▼
OHOS_SystemInit()           ← 遍历启动注册表，按优先级调用 CORE_INIT 函数
  │     ├─ CORE_INIT_PRI(BBoxInit, 1)          ← ① 创建信号量（令牌数 1）
  │     │                                        ← ② 创建 SaveErrorLog 线程
  │     │                                      ★注意：此刻线程只是"登记报名"，
  │     │                                        内核还没开始调度，它的代码一行都还没跑
  │     └─ CORE_INIT_PRI(BBoxAdapterInit, 2)   ← 注册 "SYSTEM" 模块进链表
  │                                            （内部要拿信号量：令牌现成，立刻成功）
  ▼
osKernelStart()             ← 调度器开始运转！SaveErrorLog 线程此刻才真正开始执行
  │
  ▼
系统正常运行
```

**为什么线程能"提前创建、延后执行"**：内核的线程创建接口（无论 pthread 还是 osThreadNew）
本质是"把线程登记到就绪队列"。调度器没启动时，登记了就绪也不会跑；一旦 `osKernelStart()`，
就绪线程立即被调度。这个机制是本次改造"启动前调用 osThreadNew 安全"的关键依据（详见 14.6）。

## 8. 三个运行场景故事

### 场景 A：正常启动（全程不惊动黑盒）

1. BBoxInit 创建信号量 `g_opsListSem`（初始令牌 1 = 车位空着）；
2. BBoxInit 创建后台线程 SaveErrorLog（报名，未开跑）；
3. BBoxAdapterInit 注册 SYSTEM 模块：拿令牌 → 检查链表 → 插入节点 → 还令牌；
4. 内核启动，SaveErrorLog 开跑：
   - 从 `GetFaultLogPath()` 取日志路径，截出目录名；
   - `osDelay(1000ms)` 等文件系统就绪；
   - **阻塞**拿令牌（拿到后一直不还，作为"注册表被后台占用"的标记）；
   - 遍历注册表，对每个有 GetLastLogInfo/SaveLastLog 的模块执行"取日志+存日志"；
   - 还令牌，线程结束（一次性任务）。
5. 系统正常运行，各模块随时可以注册/上报。

### 场景 B：模块报错（needSysReset=0，温和路径）

1. 某模块检测到异常，调用 `BBoxNotifyError("EVENT_X", "WIFI", "xxx 错误", 0)`；
2. 黑盒等 1000ms 让文件系统就绪；
3. **非阻塞**尝试拿令牌（超时 0）：拿到 → 继续；拿不到（后台线程正占用）→ 打日志放弃；
4. 在注册表里按名字找 "WIFI"；
5. 找到后：`Dump` 回调有 → 调用它转储现场；`Reset` 回调有 → 调用它做复位前处理；
   两者都没有 → 走默认路径 `SaveBasicErrorInfo`（格式化错误头 → 写文件 → 上传）；
6. 还令牌，返回。

### 场景 C：致命错误（needSysReset=1，复位路径）

1. `BBoxNotifyError("PANIC", "SYSTEM", "xxx", 1)`；
2. **跳过等待、跳过拿令牌**（设计意图：都致命了，锁被别人占着也别等，直接冲进去干活——
   先保现场要紧，锁破坏了也无所谓，马上要复位了）；
3. 找到模块，执行 Dump / Reset 回调；
4. 调用 `RebootSystem()`（平台弱实现）复位系统。

**一句话小结**：注册表 + 通知分发 + 后台保存线程是黑盒三件套；一个二元信号量保护注册表；
启动阶段"创建不执行"、运行阶段"阻塞/非阻塞看场景、复位路径绕过锁"——记住这张全景图，代码就顺了。

---

# 第三部分 代码逐函数精讲篇

> 本部分逐函数拆解 blackbox_core.c（改造后代码），每段代码附行内教学注释（`/*! ... */`）。
> 行号均以改造后文件为准。涉及的每个接口在第四部分有专章详解。

## 9. blackbox_core.c 八个函数逐一精讲

### 9.0 文件头部与全局变量

```c
#include "blackbox.h"            /*! 组件对外 API + ErrorInfo/ModuleOps 定义 */
#include "blackbox_adapter.h"    /*! 平台适配接口声明（改造后已无 LOS 声明） */
#include "blackbox_detector.h"   /*! 上传桩接口 */
#include "cmsis_os2.h"           /*! 改造新增：CMSIS-RTOS2 标准接口头（替换原 pthread.h） */
#include "ohos_init.h"           /*! CORE_INIT_PRI 启动注册宏 */
#include "ohos_types.h"
#include "securec.h"             /*! 安全字符串函数 memset_s/strncpy_s 等 */
#include "utils_list.h"          /*! 双向链表 */

#define LOG_ROOT_DIR_WAIT_TIME   1000     /*! 等日志根目录的时长：1000 毫秒 */
#define LOG_ROOT_DIR_WAIT_COUNT  1        /*! 等几次：1 次 */
#define BLACKBOX_TASK_STACK_SIZE 0x1000   /*! 改造新增：后台线程栈大小 4096 字节 */

struct BBoxOps {                 /*! 注册表节点 = 链表节点 + 模块登记表 */
    UTILS_DL_LIST opsList;
    struct ModuleOps ops;
};

static UTILS_DL_LIST_HEAD(g_opsList);       /*! 注册表链表头（全局唯一） */
static osSemaphoreId_t g_opsListSem;        /*! 改造后：信号量句柄（原 unsigned int LOS 句柄） */
```

> 改造点对照：原文件 `#include "pthread.h"`、3 个 LOS_ 兜底宏（`LOS_WAIT_FOREVER=0xFFFFFFFF` 等）
> 已删除；`g_opsListSem` 类型由 `unsigned int` 改为 `osSemaphoreId_t`。

### 9.1 `GetDirName` —— 从完整路径截出目录名

```c
static void GetDirName(char *dirBuf, unsigned int dirBufSize, const char *path)
{
    if (dirBuf == NULL || dirBufSize == 0 || path == NULL) {   /*! 参数防御 */
        BBOX_PRINT_ERR(...);
        return;
    }

    const char *end = path + strlen(path);      /*! end 指向字符串末尾 */
    while (*end != '/' && end >= path) {        /*! 从后往前找最后一个 '/' */
        end--;
    }
    if (end >= path) {                          /*! 找到了 '/' */
        (void)memset_s(dirBuf, dirBufSize, 0, dirBufSize);
        if (strncpy_s(dirBuf, dirBufSize - 1, path, end - path + strlen("/")) != EOK) {
            BBOX_PRINT_ERR(...);                /*! 拷贝含 '/' 的前缀 = 目录名 */
        }
    } else {                                    /*! 没找到 '/' */
        BBOX_PRINT_ERR("no / has been found!\n");
    }
}
```

**逐段讲解**：把 `/data/fault.log` 变成 `/data/`。纯字符串处理，不涉及内核接口，改造未动。
输入 `path` 为空串时 end 越过 path 起点，走"没找到 /"分支，打印错误——安全。

### 9.2 `FormatErrorInfo` —— 把三个字段安全地装进 ErrorInfo

```c
static void FormatErrorInfo(struct ErrorInfo *info,
    const char event[EVENT_MAX_LEN],
    const char module[MODULE_MAX_LEN],
    const char errorDesc[ERROR_DESC_MAX_LEN])
{
    if (info == NULL || event == NULL || module == NULL || errorDesc == NULL) {
        BBOX_PRINT_ERR(...);
        return;
    }
    (void)memset_s(info, sizeof(*info), 0, sizeof(*info));   /*! 先清零整张事故报告单 */
    if (strncpy_s(info->event, sizeof(info->event), event,    /*! 逐字段安全拷贝 */
        Min(strlen(event), sizeof(info->event) - 1)) != EOK) { /*! Min 宏防溢出 */
        BBOX_PRINT_ERR(...);
    }
    /*! module、errorDesc 同套路拷贝（代码略） */
}
```

**逐段讲解**：用 securec 的 `memset_s`/`strncpy_s`（带长度上限的"安全版"内存/字符串函数）
把用户传入的三个字段填进 `ErrorInfo`，超长自动截断。不涉及内核接口，改造未动。

### 9.3 `WaitForLogRootDir` —— 等文件系统就绪（★改造重点：osDelay）

```c
static void WaitForLogRootDir(const char *rootDir)
{
    int i = 0;

    if (rootDir == NULL) {
        BBOX_PRINT_ERR("rootDir: %p\n", rootDir);
        return;
    }
    BBOX_PRINT_INFO("wait for log root dir [%s] begin!\n", rootDir);
    while (i++ < LOG_ROOT_DIR_WAIT_COUNT) {           /*! 循环 1 次 */
        osDelay(LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / 1000);  /*! ★改造点 */
    }
    BBOX_PRINT_INFO("wait for log root dir [%s] end!\n", rootDir);
}
```

**改造前后对照**：

```c
/* 改造前 */  LOS_Msleep(LOG_ROOT_DIR_WAIT_TIME);          /* 单位：毫秒 */
/* 改造后 */  osDelay(LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / 1000);  /* 单位：tick */
```

**为什么必须换算**：`LOS_Msleep` 的参数是**毫秒**；`osDelay` 的参数是 **tick 数**。
直接把 1000 传进去，在 1000Hz 内核上恰好是 1000ms（碰巧对），但在 100Hz 内核上就是 **10 秒**（错 10 倍）。
所以用 `osKernelGetTickFreq()` 现场查询内核频率再换算：

```
tick 数 = 毫秒 × 频率 / 1000
        = 1000 × 1000 / 1000 = 1000 tick（WS63 上 = 1000ms）✓
        = 1000 × 100  / 1000 =  100 tick（100Hz 内核上 = 1000ms）✓
```

这是本次改造**最容易出错的点**，也是端到端验证的重点观察项
（启动日志里 begin/end 两条打印的时间戳应相差 ≈1000ms，详见 18.3 的 V2 验证点）。

### 9.4 `SaveBasicErrorInfo` —— 默认的错误落盘路径

```c
static void SaveBasicErrorInfo(const char *filePath, struct ErrorInfo *info)
{
    char *buf = NULL;

    if (filePath == NULL || info == NULL) {
        BBOX_PRINT_ERR(...);
        return;
    }
    buf = malloc(ERROR_INFO_MAX_LEN);               /*! 堆上申请 768 字节缓冲 */
    if (buf == NULL) {
        BBOX_PRINT_ERR("malloc failed!\n");
        return;
    }
    (void)memset_s(buf, ERROR_INFO_MAX_LEN, 0, ERROR_INFO_MAX_LEN);
    if (snprintf_s(buf, ERROR_INFO_MAX_LEN, ERROR_INFO_MAX_LEN - 1,
        ERROR_INFO_HEADER ERROR_INFO_HEADER_FORMAT,       /*! "#### error info ####\r\n" + 格式化 */
        info->event, info->module, info->errorDesc) != -1) {
        *(buf + ERROR_INFO_MAX_LEN - 1) = '\0';           /*! 保证以 '\0' 结尾 */
        (void)FullWriteFile(filePath, buf, strlen(buf), 0); /*! 平台适配接口：写文件 */
    } else {
        PRINT_ERR("buf is not enough or snprintf_s failed\n");
    }
    free(buf);                                       /*! 释放缓冲 */
    BBOX_PRINT_INFO("[%s] starts uploading event [%s]\n", info->module, info->event);
    (void)UploadEventByFile(filePath);               /*! 上传桩（detector） */
    BBOX_PRINT_INFO("[%s] ends uploading event [%s]\n", info->module, info->event);
}
```

**逐段讲解**：当出错的模块**没登记 Dump 也没登记 Reset** 时走这条默认路径——
把错误信息格式化成一页固定格式的文本，调平台接口 `FullWriteFile` 写入日志文件，
再调 `UploadEventByFile` 上传。`FullWriteFile`/`UploadEventByFile` 都是平台桩
（WS63 上是空实现，见 10/11 章）。不涉及内核接口，改造未动。

### 9.5 `SaveErrorLog` —— 后台保存线程体（★改造点：签名 + 阻塞信号量）

```c
static void SaveErrorLog(void *param)               /*! ★改造：原 void* SaveErrorLog(...) */
{
    (void)param;
    struct ErrorInfo *info = NULL;
    struct BBoxOps *ops = NULL;
    char dirName[PATH_MAX_LEN] = { 0 };

    info = malloc(sizeof(*info));                   /*! 申请事故报告单（堆，防栈溢出） */
    if (info == NULL) {
        BBOX_PRINT_ERR("malloc failed!\n");
        return;                                     /*! ★改造：原 return NULL; */
    }

    GetDirName(dirName, sizeof(dirName), GetFaultLogPath());  /*! 取日志目录名 */
    WaitForLogRootDir(dirName);                     /*! 等 1000ms 文件系统就绪 */
    if (osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK) {  /*! ★改造：阻塞拿令牌 */
        BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
        free(info);
        return;                                     /*! ★改造：原 return NULL; */
    }
    UTILS_DL_LIST_FOR_EACH_ENTRY(ops, &g_opsList, struct BBoxOps, opsList) {  /*! 遍历注册表 */
        if (ops == NULL) {
            continue;
        }
        if (ops->ops.GetLastLogInfo != NULL && ops->ops.SaveLastLog != NULL) {
            (void)memset_s(info, sizeof(*info), 0, sizeof(*info));
            if (ops->ops.GetLastLogInfo(info) != 0) {       /*! 模块自己填"最后日志" */
                BBOX_PRINT_ERR("[%s] failed to get log info!\n", ops->ops.module);
                continue;
            }
            BBOX_PRINT_INFO("[%s] starts saving log!\n", ops->ops.module);
            if (ops->ops.SaveLastLog(dirName, info) != 0) { /*! 模块自己把日志存盘 */
                BBOX_PRINT_ERR("[%s] failed to save log!\n", ops->ops.module);
            } else {
                BBOX_PRINT_INFO("[%s] ends saving log!\n", ops->ops.module);
                BBOX_PRINT_INFO("[%s] starts uploading event [%s]\n", info->module, info->event);
                (void)UploadEventByFile(GetFaultLogPath()); /*! 上传该模块的日志文件 */
                BBOX_PRINT_INFO("[%s] ends uploading event [%s]\n", info->module, info->event);
            }
        }
    }
    (void)osSemaphoreRelease(g_opsListSem);         /*! ★改造：还令牌 */
    free(info);
}
```

**逐段讲解**：
1. **为什么这个线程用阻塞等待（osWaitForever）**：它是专职干保存的，没有别的事，
   拿不到锁说明别人正在用注册表——那就安心排队等，等到为止。
2. **为什么遍历要在锁里做**：遍历期间任何人不能增删链表节点，否则遍历到一半链表被改就崩了。
3. **遍历时对每个模块**：先让模块自己 `GetLastLogInfo` 填报告单，再让模块自己 `SaveLastLog` 存盘，
   存成功才上传。全做完还令牌，线程退出（**一次性任务线程**——存完一次日志就结束了）。

> 改造点对照：线程函数签名由 `void*` 改为 `void`（CMSIS 线程函数的标准签名是
> `void func(void *)`，保持 void* 会触发编译告警）；`LOS_SemPend(..., LOS_WAIT_FOREVER)`
> 改为 `osSemaphoreAcquire(..., osWaitForever)`；`LOS_SemPost` 改为 `osSemaphoreRelease`。

### 9.6 `BBoxRegisterModuleOps` —— 模块注册（★改造点：阻塞信号量）

```c
int BBoxRegisterModuleOps(struct ModuleOps *ops)
{
    struct BBoxOps *newOps = NULL;
    struct BBoxOps *temp = NULL;

    if (ops == NULL) {
        BBOX_PRINT_ERR("ops: %p!\n", ops);
        return -1;
    }
    /* Use malloc to avoid the stack overflow */
    newOps = malloc(sizeof(*newOps));               /*! 申请节点（堆，防栈溢出） */
    if (newOps == NULL) {
        BBOX_PRINT_ERR("malloc failed!\n");
        return -1;
    }
    (void)memset_s(newOps, sizeof(*newOps), 0, sizeof(*newOps));
    (void)memcpy_s(&newOps->ops, sizeof(newOps->ops), ops, sizeof(*ops));  /*! 拷贝登记表 */

    if (osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK) {  /*! ★改造：阻塞拿锁 */
        BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
        free(newOps);
        return -1;
    }
    /* ---- 进入临界区：下面的链表操作受信号量保护 ---- */
    if (UtilsListEmpty(&g_opsList)) {
        goto __out;                                 /*! 表空 → 直接插 */
    }
    UTILS_DL_LIST_FOR_EACH_ENTRY(temp, &g_opsList, struct BBoxOps, opsList) {
        if (strcmp(temp->ops.module, ops->module) == 0) {   /*! 查重：模块名已存在？ */
            BBOX_PRINT_ERR("[%s] has been registered!\n", ops->module);
            (void)osSemaphoreRelease(g_opsListSem); /*! ★改造：还锁（失败路径也要还！） */
            free(newOps);
            return -1;                              /*! 重复注册 → 拒绝 */
        }
    }
__out:
    BBOX_PRINT_INFO("[%s] is registered successfully!\n", ops->module);
    UtilsListTailInsert(&g_opsList, &newOps->opsList);  /*! 尾插新节点 */
    (void)osSemaphoreRelease(g_opsListSem);         /*! ★改造：还锁 */
#ifdef BLACKBOX_DEBUG
    PrintModuleOps();                               /*! 调试版：打印整个注册表 */
#endif
    return 0;
}
```

**逐段讲解**：
1. **先 malloc 再拿锁**：malloc 慢，放锁外做（锁内只做链表操作，锁持有时间短 = 别人等得短）；
2. **查重依据是模块名**：同一模块名只允许注册一次；
3. **失败路径必须还锁**：重复注册的 return -1 前先 Release——忘了还锁，全系统永远拿不到令牌（死锁）；
4. **这里为什么用阻塞**：注册通常发生在启动阶段，调用者"不成功不罢休"，值得等。

> 改造点对照：`LOS_SemPend(g_opsListSem, LOS_WAIT_FOREVER) != 0` →
> `osSemaphoreAcquire(g_opsListSem, osWaitForever) != osOK`；两处 `LOS_SemPost` →
> `osSemaphoreRelease`。判错写法从 `!= 0` 改为 `!= osOK`（`osOK` 就是 0，语义完全相同）。

### 9.7 `BBoxNotifyError` —— 错误通知分发（★改造点：非阻塞信号量）

```c
int BBoxNotifyError(const char event[EVENT_MAX_LEN],
    const char module[MODULE_MAX_LEN],
    const char errorDesc[ERROR_DESC_MAX_LEN],
    int needSysReset)
{
    int findModule = 0;
    struct BBoxOps *ops = NULL;
    struct ErrorInfo *info = NULL;
    char dirName[PATH_MAX_LEN] = { 0 };

    info = malloc(sizeof(*info));
    if (info == NULL) {
        BBOX_PRINT_ERR("malloc failed!\n");
        return -1;
    }

    GetDirName(dirName, sizeof(dirName), GetFaultLogPath());
    if (needSysReset == 0) {                        /*! 温和路径才需要这些准备 */
        WaitForLogRootDir(dirName);                 /*! 等文件系统 1000ms */
        if (osSemaphoreAcquire(g_opsListSem, 0U) != osOK) {  /*! ★改造：非阻塞拿锁 */
            BBOX_PRINT_ERR("Request g_opsListSem failed!\n");
            goto __out;                             /*! 拿不到就放弃（不等待） */
        }
    }

    UTILS_DL_LIST_FOR_EACH_ENTRY(ops, &g_opsList, struct BBoxOps, opsList) {
        if (ops == NULL) {
            BBOX_PRINT_ERR("ops: %p!\n", ops);
            continue;
        }
        if (strcmp(ops->ops.module, module) != 0) { /*! 按模块名找目标 */
            continue;
        }
        FormatErrorInfo(info, event, module, errorDesc);   /*! 填事故报告单 */
        if (ops->ops.Dump == NULL && ops->ops.Reset == NULL) {
            SaveBasicErrorInfo(GetFaultLogPath(), info);   /*! 模块没登记任何回调 → 默认落盘 */
            break;
        }
        if (ops->ops.Dump != NULL) {                /*! 调用模块的现场转储回调 */
            BBOX_PRINT_INFO("[%s] starts dumping data!\n", ops->ops.module);
            ops->ops.Dump(dirName, info);
            BBOX_PRINT_INFO("[%s] ends dumping data!\n", ops->ops.module);
        }
        if (ops->ops.Reset != NULL) {               /*! 调用模块的复位前处理回调 */
            BBOX_PRINT_INFO("[%s] starts resetting!\n", ops->ops.module);
            ops->ops.Reset(info);
            BBOX_PRINT_INFO("[%s] ends resetting!\n", ops->ops.module);
        }
        findModule = 1;                             /*! 标记：找到了 */
        break;
    }
    if (needSysReset == 0) {
        (void)osSemaphoreRelease(g_opsListSem);     /*! ★改造：还锁 */
    }

__out:
    if (info != NULL) {
        free(info);
    }
    if (needSysReset != 0 && findModule != 0) {
        RebootSystem();                             /*! 致命路径：完事就复位（平台弱实现） */
    }
    return 0;
}
```

**逐段讲解（重点理解两种锁策略的设计意图）**：
1. **needSysReset == 0（温和路径）**：先等文件系统、**非阻塞**拿锁。为什么非阻塞？
   出错上报可能发生在任何上下文（甚至中断附近的紧急路径），**不能让报错的人卡住排队**——
   拿不到锁说明后台线程正忙，这次上报放弃即可（宁丢一次上报，不堵死报错者）。
2. **needSysReset != 0（致命路径）**：**跳过等待、不拿锁**直接查表执行。为什么？
   系统马上要复位了，第一要务是抢时间把现场 dump 下来——锁被别人占着也不能等，
   链表此时被并发修改的概率极低（都要死了），赌一把保现场更划算。设计上接受这个取舍。
3. **Dump 与 Reset 的区别**：Dump = 把现场数据写到日志目录；Reset = 复位前的收尾动作
   （比如把脏数据刷盘）。先 Dump 后 Reset，顺序固定。
4. 温和路径找到模块并处理完，才在 `__out` 释放锁（失败路径 `goto __out` 时**没拿到锁，
   也绝不能释放**——释放一个没拿到的锁会凭空多一个令牌，破坏互斥！代码用 `needSysReset == 0`
   的 if 把两条路径分开，保证拿过才还）。

> 改造点对照：`LOS_SemPend(g_opsListSem, LOS_NO_WAIT) != 0` →
> `osSemaphoreAcquire(g_opsListSem, 0U) != osOK`（`LOS_NO_WAIT` 就是 0，
> CMSIS 超时传 0 = 非阻塞）；`LOS_SemPost` → `osSemaphoreRelease`。

### 9.8 `BBoxInit` —— 启动初始化（★改造重点：osSemaphoreNew + osThreadNew）

**改造前**：

```c
static void BBoxInit(void)
{
    int ret = -1;
    pthread_t taskId = 0;                       /* POSIX 线程号 */

    if (LOS_BinarySemCreate(1, &g_opsListSem) != LOS_OK) {   /* 出参式：句柄写回指针 */
        BBOX_PRINT_ERR("Create binary semaphore failed!\n");
        return;
    }
    UtilsListInit(&g_opsList);
    ret = pthread_create(&taskId, NULL, SaveErrorLog, NULL); /* POSIX 创建线程 */
    if (ret != 0) {
        BBOX_PRINT_ERR("Falied to create SaveErrorLog task, ret: %d\n", ret);
    }
}
CORE_INIT_PRI(BBoxInit, 1);                     /* 启动注册：优先级 1 */
```

**改造后（blackbox_core.c:308-323）**：

```c
static void BBoxInit(void)
{
    osThreadAttr_t taskAttr = {                 /*! ★线程属性：9 字段按顺序填写 */
        "BlackBoxTask", 0, NULL, 0, NULL, BLACKBOX_TASK_STACK_SIZE, osPriorityNormal, 0, 0
    };
    /*!   ↑name        ↑attr_bits  ↑cb_mem ↑cb_size ↑stack_mem ↑stack_size ↑priority ↑tz ↑reserved */
    g_opsListSem = osSemaphoreNew(1, 1, NULL);  /*! ★返回值式：直接返回句柄 */
    /*!                              ↑max ↑initial ↑attr(NULL=默认) */
    if (g_opsListSem == NULL) {                 /*! 失败判定：句柄为 NULL */
        BBOX_PRINT_ERR("Create binary semaphore failed!\n");
        return;
    }
    UtilsListInit(&g_opsList);                  /*! 链表头初始化 */
    if (osThreadNew(SaveErrorLog, NULL, &taskAttr) == NULL) {  /*! ★创建线程 */
        BBOX_PRINT_ERR("Failed to create SaveErrorLog task!\n");
    }
}
CORE_INIT_PRI(BBoxInit, 1);
```

**逐段讲解**：
1. **`osSemaphoreNew(1, 1, NULL)`**：max=1（最多 1 个令牌）= **二元信号量**；
   initial=1（一开始就有 1 个令牌，即"车位空着"）；attr=NULL 用默认属性。
   与原 `LOS_BinarySemCreate(1, &sem)` 完全同义。
2. **成功判定方式变了**：LOS 是"函数返回错误码 + 句柄从指针参数写回"；
   CMSIS 是"函数直接返回句柄，NULL = 失败"。这是两套接口的风格差异（详见 15 章）。
3. **`osThreadNew(SaveErrorLog, NULL, &taskAttr)`**：线程函数 `SaveErrorLog`、
   参数 NULL（线程不用参数）、属性指针。
   - 线程名 "BlackBoxTask"（调试/转储任务列表时好认）；
   - 栈大小 0x1000 = 4096 字节（SaveErrorLog 的局部变量只有 256 字节 dirName，
     其余都 malloc 到堆上，4KB 绰绰有余）；
   - 优先级 osPriorityNormal = 24（与 LiteOS 默认任务优先级一致，不高不低）。
4. **线程函数签名改造**：CMSIS 规定线程函数签名是 `void func(void *)`，
   原 SaveErrorLog 是 `void* func(void *)`——不改会告警、传参不兼容，所以顺手把
   返回类型改成 void（函数体里的 `return NULL;` 对应改成 `return;`）。
5. **CORE_INIT_PRI(BBoxInit, 1)**：启动注册，优先级 1（比 BBoxAdapterInit 的 2 先执行）。
   此时调度器还没启动，osThreadNew 只是"登记报名"，线程体等 osKernelStart 后才跑——
   这个行为与原 pthread_create 完全一致（LiteOS 的线程创建也是"先入队、启动后调度"）。

**一句话小结（第三部分）**：黑盒的全部逻辑就是"注册表三件事"——注册（查重+尾插）、
通知（按名找+回调分发）、后台保存（遍历+存取+上传），全部由一个二元信号量看门；
改造只换了"锁"和"线程"的系统接口，业务逻辑一行没变。

---

## 10. blackbox_adapter.c —— 平台适配层

```c
WEAK void SystemModuleDump(const char *logDir, struct ErrorInfo *info)
{
    (void)logDir;
    (void)info;
    BBOX_PRINT_ERR("Please implement the interface according to the platform!\n");
}
```

**7 个弱符号接口**（全部同一套路：默认实现只打印"请平台实现"）：

| 接口 | 平台要干什么 |
|---|---|
| `SystemModuleDump` | SYSTEM 模块的现场转储（如转储寄存器、任务状态） |
| `SystemModuleReset` | SYSTEM 模块复位前处理 |
| `SystemModuleGetLastLogInfo` | 取系统最后日志信息 |
| `SystemModuleSaveLastLog` | 保存系统最后日志 |
| `FullWriteFile` | 把缓冲写进文件（可追加） |
| `GetFaultLogPath` | 返回故障日志文件路径 |
| `RebootSystem` | 重启系统 |

**弱符号机制**：平台（如 hi3861 的 SDK）可以用同名函数**强实现覆盖**这些弱实现；
链接器优先选强实现。WS63 平台目前没有覆盖（nm 证实全是弱符号 W），
所以黑盒在 WS63 上"只演流程、不真落盘"——这是平台适配工作，不在本组件改造范围。

**启动注册**：

```c
static void BBoxAdapterInit(void)               /*! CORE_INIT_PRI 优先级 2 */
{
    struct ModuleOps ops = {
        .module = MODULE_SYSTEM,                /*! "SYSTEM" */
        .Dump = SystemModuleDump,               /*! 挂上 4 个弱符号回调 */
        .Reset = SystemModuleReset,
        .GetLastLogInfo = SystemModuleGetLastLogInfo,
        .SaveLastLog = SystemModuleSaveLastLog,
    };
    if (BBoxRegisterModuleOps(&ops) != 0) {     /*! 走 9.6 的注册流程 */
        BBOX_PRINT_ERR("BBoxRegisterModuleOps failed!\n");
        return;
    }
}
CORE_INIT_PRI(BBoxAdapterInit, 2);
```

**隐藏测试钩子**：`#ifdef BLACKBOX_TEST` 包着一个 `BBoxTest()`（注册 MODULE_TEST +
调用一次 BBoxNotifyError）。编译时定义了 BLACKBOX_TEST 才生效，当前产品未开启。

## 11. blackbox_detector.c —— 上传桩

```c
int UploadEventByFile(const char *filePath)
{
    if (filePath == NULL) { return -1; }
    return 0;                                   /*! 空实现：等平台/云侧对接 */
}
```

两个接口（按文件/按流上传）都是**桩**：参数校验 + 返回 0。留给后续事件上传能力接入，
本组件不涉及内核接口，改造未动。

## 12. 公开头文件讲解

### 12.1 blackbox.h（对外 API）

```c
#define ERROR_INFO_MAX_LEN 768
#define EVENT_MAX_LEN      32
#define MODULE_MAX_LEN     32
#define ERROR_DESC_MAX_LEN 512
#define MODULE_SYSTEM      "SYSTEM"
#define EVENT_SYSREBOOT    "SYSREBOOT"
#define EVENT_PANIC        "PANIC"        /*! 预置事件名：内核 panic 等 9 个 */
...

int BBoxRegisterModuleOps(struct ModuleOps *ops);     /*! 对外仅这两个函数 */
int BBoxNotifyError(const char event[EVENT_MAX_LEN],
    const char module[MODULE_MAX_LEN],
    const char errorDesc[ERROR_DESC_MAX_LEN],
    int needSysReset);
```

对外 API 只有两个：**注册**和**通知**。任何模块想用黑盒，只需这两个函数。

### 12.2 blackbox_adapter.h（平台接口声明，改造过）

改造前里面有 3 行内核函数声明（`extern unsigned int LOS_BinarySemCreate(...)` 等）——
这是把内核头文件的东西抄进了公开头（**公开接口污染**）。改造后删除，
公开头只保留组件自己的 7 个平台适配接口声明 + WEAK 宏定义。

---

# 第四部分 接口深度解读篇（LOS 与 CMSIS 从零讲）

## 13. LiteOS 接口逐个详解（改造前用到的 4 个）

> LiteOS 是 OpenHarmony 自研轻量内核。接口返回错误码：0（LOS_OK）表示成功，非 0 表示失败。
> 类型约定：UINT32 = 无符号 32 位整数；UINT16 = 无符号 16 位。

### 13.1 `LOS_BinarySemCreate` —— 创建二元信号量

```c
UINT32 LOS_BinarySemCreate(UINT16 count, UINT32 *semHandle);
```

| 项 | 说明 |
|---|---|
| 参数 count | **初始令牌数**：1 = 创建时令牌可用；0 = 创建时令牌已被占用 |
| 参数 semHandle | **出参**：函数把信号量句柄写回这个指针指向的变量 |
| 返回 | LOS_OK(0) 成功；其他为错误码 |
| "二元"含义 | 信号量令牌上限 = 1（要么 0 要么 1，就像只有 1 个车位） |

**注意**：句柄是"出参"模式——先声明 `unsigned int sem;`，把 `&sem` 传进去，函数成功后在 `sem` 里拿句柄。

### 13.2 `LOS_SemPend` —— P 操作（拿令牌）

```c
UINT32 LOS_SemPend(UINT32 semHandle, UINT32 timeout);
```

| 项 | 说明 |
|---|---|
| 参数 semHandle | 创建时拿到的句柄 |
| 参数 timeout | **毫秒**。三个特殊值：`LOS_NO_WAIT`(0)=非阻塞；`LOS_WAIT_FOREVER`(0xFFFFFFFF)=永久阻塞；N=最多等 N 毫秒 |
| 返回 | LOS_OK 拿到令牌；`LOS_ERRNO_SEM_TIMEOUT` 超时没拿到；其他错误码 |

（`LOS_NO_WAIT`/`LOS_WAIT_FOREVER` 定义于内核 `los_base.h:84/90`。）

### 13.3 `LOS_SemPost` —— V 操作（还令牌）

```c
UINT32 LOS_SemPost(UINT32 semHandle);
```

| 项 | 说明 |
|---|---|
| 返回 | LOS_OK；`LOS_ERRNO_SEM_OVERFLOW` = 令牌已满还硬还（二元信号量上重复释放） |

### 13.4 `LOS_Msleep` —— 毫秒延时

```c
VOID LOS_Msleep(UINT32 msecs);      /* los_base.h:287 */
```

| 项 | 说明 |
|---|---|
| 参数 | **毫秒数**（M 就是 ms 的意思） |
| 效果 | 当前任务挂起（让出 CPU 去睡觉），时间到再被唤醒 |
| 单位 | **毫秒** ← 记住这个，和 CMSIS 的 osDelay（tick）不同！ |

## 14. CMSIS-RTOS2 接口逐个详解（改造后用到的 8 个）

> CMSIS-RTOS2 是 ARM 的跨内核标准 API。特点：**返回值式句柄**（函数直接返回句柄/状态，
> 不靠出参）、错误状态统一为 `osStatus_t` 枚举。以下定义见
> `third_party/cmsis/CMSIS/RTOS2/Include/cmsis_os2.h`。

### 14.1 `osSemaphoreId_t` —— 信号量句柄类型

```c
typedef struct os_semaphore_def *osSemaphoreId_t;   /* 本质是指针 */
```

类比：银行小票。黑盒的 `g_opsListSem` 就是这个类型。

### 14.2 `osSemaphoreNew` —— 创建信号量

```c
osSemaphoreId_t osSemaphoreNew(uint32_t max_count, uint32_t initial_count,
                               const osSemaphoreAttr_t *attr);
```

| 参数 | 说明 |
|---|---|
| max_count | 令牌上限。**=1 即二元信号量**（等价 LOS_BinarySemCreate） |
| initial_count | 初始令牌数（本组件传 1 = 一上来令牌可用） |
| attr | 属性（名称等），NULL = 默认 |
| 返回 | 句柄；**NULL = 创建失败** |

对比 LOS 版：LOS 是"返回错误码 + 出参句柄"，CMSIS 是"直接返回句柄，NULL 判失败"。
两种风格无优劣，改代码时把判定从 `!= LOS_OK` 换成 `== NULL` 即可，语义完全一致。
树内核 LiteOS-M 的实现里，`max_count == 1` 时内部就是调用 `LOS_BinarySemCreate`
（`kernel/liteos_m/kal/cmsis/cmsis_liteos2.c:1120`），所以底层是同一个东西。

### 14.3 `osSemaphoreAcquire` —— P 操作（拿令牌）

```c
osStatus_t osSemaphoreAcquire(osSemaphoreId_t semaphore_id, uint32_t timeout);
```

| 参数 | 说明 |
|---|---|
| semaphore_id | 句柄 |
| timeout | **tick 数**：`osWaitForever`(0xFFFFFFFFU)=永久阻塞；**0=非阻塞**；N=最多等 N tick |
| 返回 | 枚举 `osStatus_t`：`osOK`(0) 成功；`osErrorTimeout` 超时；`osErrorResource` 资源错；`osErrorParameter` 参数错 |

**本组件三处调用**：
- `osSemaphoreAcquire(sem, osWaitForever)` ×2（后台线程、注册路径）——永久等；
- `osSemaphoreAcquire(sem, 0U)` ×1（通知路径）——非阻塞。

> 细节提醒：`osWaitForever` 的值 `0xFFFFFFFFU` 与旧代码里 `LOS_WAIT_FOREVER` 的
> `0xFFFFFFFF` **数值一模一样**——只是常数搬了家（从内核头文件搬到 CMSIS 标准头）。

### 14.4 `osSemaphoreRelease` —— V 操作（还令牌）

```c
osStatus_t osSemaphoreRelease(osSemaphoreId_t semaphore_id);
```

成功返回 `osOK`；**令牌已满**时返回 `osErrorResource`（对应 LOS 的 SEM_OVERFLOW）。
本组件 4 处释放全部有"同函数内先成功 Acquire"的前置条件，满员释放路径不可达。

### 14.5 `osDelay` 与 `osKernelGetTickFreq` —— ★本次改造的核心知识点

```c
osStatus_t osDelay(uint32_t ticks);          /* 延时 ticks 个 tick */
uint32_t   osKernelGetTickFreq(void);        /* 查询内核 tick 频率（Hz） */
```

**单位差异（必考）**：

| 接口 | 单位 | 想延时 1 秒在 1000Hz 内核传 | 在 100Hz 内核传 |
|---|---|---|---|
| `LOS_Msleep` | 毫秒 | 1000 | 1000（内核自动换算） |
| `osDelay` | **tick** | 1000 | **100**（自己换算，否则差 10 倍） |

**换算公式**（本组件 9.3 节用到的就是这个）：

```
tick 数 = 毫秒数 × osKernelGetTickFreq() / 1000
```

用 `osKernelGetTickFreq()` 现场查询而不是写死 1000，保证组件在 1000Hz（WS63）
和 100Hz（树内核 qemu riscv32 产品）上都正确延时 1000ms。

### 14.6 `osThreadNew` —— 创建线程

```c
osThreadId_t osThreadNew(osThreadFunc_t func, void *argument, const osThreadAttr_t *attr);
```

| 参数 | 说明 |
|---|---|
| func | 线程函数。**规定签名 `void func(void *)`**——本组件因此把 SaveErrorLog 从 `void*` 改成 `void` |
| argument | 传给线程函数的参数（本组件传 NULL） |
| attr | 线程属性，NULL = 全默认；本组件显式传属性 |
| 返回 | 线程句柄；**NULL = 创建失败** |

**`osThreadAttr_t` 九字段逐字段**（本组件按位序初始化）：

```c
osThreadAttr_t taskAttr = {
    "BlackBoxTask",      /* ① name        线程名（调试、任务列表里显示） */
    0,                   /* ② attr_bits   属性位（0 = 无特殊） */
    NULL,                /* ③ cb_mem      线程控制块内存（NULL = 内核分配） */
    0,                   /* ④ cb_size     控制块大小（随 cb_mem，0 = 默认） */
    NULL,                /* ⑤ stack_mem   栈内存（NULL = 内核分配） */
    BLACKBOX_TASK_STACK_SIZE, /* ⑥ stack_size 栈大小：0x1000 = 4096 字节 */
    osPriorityNormal,    /* ⑦ priority    优先级：24（与 LiteOS 默认一致） */
    0,                   /* ⑧ tz_module   信任区模块（安全扩展，普通场景 0） */
    0                    /* ⑨ reserved    保留字段（个别内核用作 affinity_mask） */
};
```

**启动前创建线程安全吗？**（评审高频问题，答案见 18.3 Q&A）
安全。树内核的 osThreadNew 底层是 `LOS_TaskCreate`，它在调度器未启动时只是把任务
登记进就绪队列，`osKernelStart()` 后才真正运行——与改造前 pthread_create 的行为完全一致。

### 14.7 常用常量速查

| 常量 | 值 | 含义 |
|---|---|---|
| `osOK` | 0 | 操作成功（判错写法 `!= osOK` 等价旧写法 `!= 0`） |
| `osWaitForever` | 0xFFFFFFFFU | 永久阻塞等待 |
| `osPriorityNormal` | 24 | 普通任务优先级 |

## 15. 对照总表与语义差异清单

### 15.1 逐接口映射表

| 原接口（LOS/POSIX） | 新接口（CMSIS-RTOS2） | 功能 |
|---|---|---|
| `LOS_BinarySemCreate(1, &sem)` | `osSemaphoreNew(1, 1, NULL)` | 创建二元信号量 |
| `LOS_SemPend(sem, LOS_WAIT_FOREVER)` | `osSemaphoreAcquire(sem, osWaitForever)` | 阻塞拿令牌 |
| `LOS_SemPend(sem, LOS_NO_WAIT)` | `osSemaphoreAcquire(sem, 0U)` | 非阻塞拿令牌 |
| `LOS_SemPost(sem)` | `osSemaphoreRelease(sem)` | 还令牌 |
| `LOS_Msleep(ms)` | `osDelay(ms * osKernelGetTickFreq() / 1000)` | 延时 |
| `pthread_create(&tid, NULL, fn, NULL)` | `osThreadNew(fn, NULL, &attr)` | 创建线程 |

### 15.2 三大语义差异与处理方式

| 差异 | LOS | CMSIS | 本组件怎么处理 |
|---|---|---|---|
| **时间单位** | 毫秒（LOS_Msleep、LOS_SemPend 超时） | tick（osDelay、Acquire 超时） | osDelay 处按 15.1 公式换算；Acquire 只用 0/无限两种特殊值，无换算问题 |
| **句柄传递风格** | 返回错误码 + **出参**写句柄 | **返回值式**直接给句柄/NULL | 创建处改写为"接返回值判 NULL" |
| **错误码体系** | LOS_OK / LOS_ERRNO_SEM_TIMEOUT / _OVERFLOW | osStatus_t：osOK / osErrorTimeout / osErrorResource / osErrorParameter | 判错统一 `!= osOK`（osOK=0 与旧判法等价）；旧代码无需区分具体错误码，新代码同样不区分 |

**一句话小结（第四部分）**：LOS 接口 = 出参句柄 + 毫秒 + 私有错误码；
CMSIS 接口 = 返回值句柄 + tick + 标准状态枚举。差异就三处，本组件逐处都做了等价处理。

---

# 第五部分 改造讲解篇（评审会直接使用）

## 16. 13 个改动点逐个"原来 / 现在 / 为什么"

> 与《接口改造清单》Excel 一一对应，行号以改造后文件为准。

### 16.1 blackbox_core.c（9 处）

| # | 位置 | 原来 | 现在 | 为什么 |
|---|---|---|---|---|
| 1 | :19 | `#include "pthread.h"` | `#include "cmsis_os2.h"` | 专项要求 mini 组件统一 CMSIS；pthread 头不再需要 |
| 2 | :26-28 | 局部定义 LOS_WAIT_FOREVER/NO_WAIT/OK 兜底宏 | 删除，改用 CMSIS 标准常量；新增 BLACKBOX_TASK_STACK_SIZE | 兜底宏是内核常量复制品，随 LOS 接口一并退场；栈大小宏供线程属性使用 |
| 3 | :39 | `static unsigned int g_opsListSem` | `static osSemaphoreId_t g_opsListSem` | 句柄类型跟随新接口体系 |
| 4 | :99 | `LOS_Msleep(1000)` | `osDelay(1000 * osKernelGetTickFreq() / 1000)` | 单位差异：ms → tick，按内核频率现场换算，两种频率内核下都精确延时 1000ms |
| 5 | :150 / :214 | `LOS_SemPend(sem, LOS_WAIT_FOREVER) != 0`（2 处） | `osSemaphoreAcquire(sem, osWaitForever) != osOK` | 阻塞等待等价替换；osWaitForever 与旧宏数值相同 |
| 6 | :261 | `LOS_SemPend(sem, LOS_NO_WAIT) != 0` | `osSemaphoreAcquire(sem, 0U) != osOK` | 非阻塞等价替换：0 超时即非阻塞 |
| 7 | :177/:225/:234/:294 | `LOS_SemPost(sem)`（4 处） | `osSemaphoreRelease(sem)` | V 操作等价替换；4 处均有 Acquire 前置 |
| 8 | :314 | `LOS_BinarySemCreate(1, &sem) != LOS_OK` | `sem = osSemaphoreNew(1, 1, NULL); 判 NULL` | 二元信号量创建；max=1 底层即 LOS_BinarySemCreate；判定风格随返回值式句柄调整 |
| 9 | :320 | `pthread_create(&tid, NULL, SaveErrorLog, NULL)` | `osThreadNew(SaveErrorLog, NULL, &taskAttr)` | 线程创建等价替换；SaveErrorLog 签名 void*→void 匹配 osThreadFunc_t；属性显式化（名/栈 0x1000/osPriorityNormal） |

### 16.2 公开头与构建（4 处）

| # | 位置 | 原来 | 现在 | 为什么 |
|---|---|---|---|---|
| 10 | kits/blackbox_adapter.h | 3 行 LOS_ 内核函数 extern 声明 | 删除 | 公开头只应声明组件自己的 API，内核声明属于接口污染 |
| 11 | innerkits/blackbox_adapter.h | 同上 | 删除（与 kits 副本同步） | 两份头文件保持一致 |
| 12 | BUILD.gn :26 | 无 cmsis 头文件路径 | include_dirs 首位新增 `//third_party/cmsis/CMSIS/RTOS2/Include` | 提供 cmsis_os2.h 搜索路径；放首位保证优先命中；不 dep 树内核（预编译内核产品会被误拉入） |
| 13 | bundle.json :26-27 | `"third_party": []` | `"third_party": ["cmsis"]` | 依赖元数据补全，纯声明无编译影响 |

## 17. 行为等价性论证（白话版，5 条）

1. **信号量没变**：`osSemaphoreNew(1,1,NULL)` 在内核底层就是原来的 `LOS_BinarySemCreate(1)`——
   同一个内核对象，初始令牌同样是 1；
2. **P/V 语义没变**：Acquire(∞)=原 Pend(WAIT_FOREVER)；Acquire(0)=原 Pend(NO_WAIT)；
   Release=原 Post；所有判错点成功/失败分支与原代码逐一对应；
3. **延时更准了**：原来是"写死 1000ms"，现在按内核频率换算，在任何 tick 频率的产品上都精确 1000ms；
4. **线程行为没变**：都是"创建即入队、内核启动后运行"，栈和优先级显式给到与原默认一致的合理值；
5. **错误路径逐条保留**：malloc 失败、拿锁失败、重复注册、缺回调走默认路径——
   每一条 return/-1/打日志的行为都与改造前相同。

## 18. 评审讲解素材

### 18.1 30 秒电梯陈述

> blackbox_lite 是轻量系统的软件黑盒——各模块向它注册诊断回调，出错时它分发通知、
> 收集现场、保存日志。本次改造把它从 LiteOS 私有接口（LOS_Sem*/LOS_Msleep/pthread）
> 迁移到 CMSIS-RTOS2 标准接口（osSemaphore*/osDelay/osThreadNew），业务逻辑零改动，
> 行为等价已逐项论证，nearlink_dk_3863 编译通过、符号检查无 LOS 残留、固件正常生成。

### 18.2 5 分钟标准讲解脚本提纲

1. **组件是什么**（30 秒）：黑匣子类比 + 注册/通知/后台保存三件套图；
2. **整体逻辑**（90 秒）：启动时序（先建锁和线程、再注册 SYSTEM、内核启动后线程开跑）
   + 三个场景故事（正常/温和报错/致命复位），重点讲两种锁策略的设计意图；
3. **改造内容**（90 秒）：13 个改动点对照表快速过一遍，重点停两个：
   ① osDelay 的 tick 换算（ms→tick，为什么必须用 osKernelGetTickFreq）；
   ② osThreadNew 的线程属性（签名 void、九字段、栈 0x1000、osPriorityNormal）；
4. **等价性与验证**（60 秒）：5 条等价性论证 + 编译/符号/产物三项验证证据；
5. **边界说明**（30 秒）：WS63 上 7 个平台适配接口是弱符号桩，落盘能力待平台接入；
   树内核路径未做产品级验证（当前无产品编译本仓）。

### 18.3 常见提问 Q&A 预备（10 问）

| # | 问题 | 标准答案（≤3 句） |
|---|---|---|
| Q1 | 为什么不用 #ifdef 做 LOS/CMSIS 双分支？ | 本组件 bundle.json 声明 mini-only，专项规定 mini 统一 CMSIS；无共编场景，单实现最简、最好维护 |
| Q2 | 为什么 osDelay 要做 tick 换算？ | osDelay 单位是 tick 而旧接口是毫秒；不同产品 tick 频率不同（WS63 1000Hz、树内核产品 100Hz），用 osKernelGetTickFreq 现场换算保证任何产品都延时精确 |
| Q3 | 为什么栈选 0x1000？ | SaveErrorLog 局部变量仅 256B dirName，缓冲全 malloc 到堆；4KB 有充足裕量且在组件 ~5KB RAM 预算内 |
| Q4 | 调度器启动前创建线程安全吗？ | 安全。树内核 osThreadNew 底层 LOS_TaskCreate 在调度器未启动时只入队不运行，osKernelStart 后才调度，与原来 pthread_create 行为一致 |
| Q5 | BBoxNotifyError 为什么用非阻塞拿锁？ | 报错可能发生在紧急上下文，上报者不能被锁卡住排队；拿不到说明后台线程在忙，宁丢一次上报也不堵死报错者 |
| Q6 | needSysReset=1 为什么绕过锁？ | 致命路径第一要务是抢时间保现场，系统马上复位，锁的严格性优先级低于数据保全，属有意取舍 |
| Q7 | 公开头为什么删 LOS 声明？ | 那 3 行是内核头文件声明的复制品，不属于组件 API；专项要求消除 LOS 依赖，且全树无消费者 |
| Q8 | 为什么 include 目录放首位、不 dep 树内核？ | 首位保证 third_party 标准头优先命中；本产品是预编译内核，dep 树内核目标会把整棵树内核拉进构建 |
| Q9 | 为什么不动 BBoxDriverInit 死声明？ | 与本次适配无直接关系，评审决策保留，后续单独清理 |
| Q10 | WS63 上为什么没有真正落盘？ | 7 个平台适配接口是弱符号桩（nm 证实无强实现）；落盘属平台适配层职责，本组件只负责逻辑，接口已备好 |

---

# 第六部分 附录

## 19. 术语表（中英对照）

| 术语 | 英文 | 一句话解释 |
|---|---|---|
| 实时操作系统 | RTOS | 快速响应、可预测调度的嵌入式操作系统 |
| 任务/线程 | Task/Thread | 独立运行的代码段，CPU 在其间切换 |
| 调度器 | Scheduler | 内核中决定"下一个跑谁"的部件 |
| 信号量 | Semaphore | 计数令牌，P（拿）/V（还）保护共享资源 |
| 二元信号量 | Binary Semaphore | 令牌上限为 1 的信号量（0/1 两种状态） |
| 临界区 | Critical Section | 同一时刻只允许一个任务进入的代码区 |
| 阻塞/非阻塞 | Blocking/Non-blocking | 拿不到资源就一直等 / 立刻返回失败 |
| 时钟节拍 | tick | 内核心跳，延时的最小单位 |
| tick 频率 | tick frequency | 每秒心跳数（Hz），如 1000Hz=1tick/ms |
| 句柄 | Handle | 操作系统对象的"取号小票" |
| 弱符号 | Weak symbol | 可被强实现覆盖的默认实现 |
| 内核 | Kernel | 操作系统核心（任务管理/内存/中断） |
| 双向链表 | Doubly linked list | 每个节点记前后邻居的动态数据结构 |
| 启动注册 | CORE_INIT | 系统启动时按优先级自动调用的注册机制 |
| 私有接口 | Proprietary API | 仅某内核有的接口（如 LOS_*） |
| 标准接口 | Standard API | 跨实现通用的接口规范（如 CMSIS-RTOS2） |
| 桩 | Stub | 空/默认实现，等后续对接 |

## 20. 文件路径索引与参考

**组件文件（改造后）**：
- `base/hiviewdfx/blackbox_lite/blackbox_core.c`（核心逻辑，323 行）
- `base/hiviewdfx/blackbox_lite/blackbox_adapter.c`（平台适配层）
- `base/hiviewdfx/blackbox_lite/blackbox_detector.c/.h`（上传桩）
- `base/hiviewdfx/blackbox_lite/interfaces/native/kits/blackbox.h`（对外 API + 数据结构）
- `base/hiviewdfx/blackbox_lite/interfaces/native/{kits,innerkits}/blackbox_adapter.h`（平台接口声明）
- `base/hiviewdfx/blackbox_lite/BUILD.gn`、`bundle.json`

**接口参考**：
- CMSIS-RTOS2 标准头：`third_party/cmsis/CMSIS/RTOS2/Include/cmsis_os2.h`
  （osWaitForever:193、osThreadNew:429、osDelay:586、osSemaphoreNew:715、osSemaphoreAcquire:726、osSemaphoreRelease:731）
- 树内核 CMSIS 实现：`kernel/liteos_m/kal/cmsis/cmsis_liteos2.c`（osThreadNew:246、osDelay:643、osSemaphoreNew:1120）
- LiteOS 信号量头：`los_sem.h`（LOS_BinarySemCreate:213、LOS_SemPend:273、错误码 :130/:140）
- LiteOS 基础头：`los_base.h`（LOS_NO_WAIT:84、LOS_WAIT_FOREVER:90、LOS_Msleep:287）

**配套材料**：
- 评审材料（问题分析/方案/验证）：`/home/houcq/workspace/blackbox_lite_CMSIS适配评审材料.md`
- 接口改造清单 Excel：`~/resource/blackbox_lite_接口改造清单.xlsx`

---

*全文完。建议讲前流程：① 通读第一、二部分建立概念与全景 → ② 精读第三部分逐函数 →
③ 第四部分查接口细节 → ④ 背熟 18.1/18.3 → ⑤ 用 18.2 提纲演练一遍。*
