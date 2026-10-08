
### 需求背景

OpenHarmony解决方案为支持多内核需求，切换内核不影响上层服务&框架功能，需要上层部件统一适配CMSIS&POSIX接口，替代使用操作系统原生接口（比如LOS_xx）。排查中发现blackbox_lite组件使用了LiteOS-M原生接口及pthread接口，需要替换成CMSIS-RTOS2标准接口

#### blackbox_lite组件介绍

**黑盒组件**（blackbox）类似黑匣子：

> **当系统或某个模块发生致命错误（panic、看门狗复位、掉电、系统重启）时，
> 在"倒下"之前，把各个模块的关键现场信息（错误事件、模块名、错误描述、各模块自带的诊断数据）
> 收集、保存下来，供事后分析定位问题。

**使用场景：**

| 场景                 | 行为                                  |
| ------------------ | ----------------------------------- |
| 内核 panic / 系统看门狗复位 | 复位前把各模块的关键寄存器、状态信息 dump 到日志文件       |
| 掉电 / 异常关机          | 保存最后痕迹                              |
| 某个业务模块检测到自身异常      | 调用黑盒接口记录事件，按需触发模块自检（Dump）或重启（Reset） |

**具体组件代码介绍见文末[[CMSIS&POSIX接口适配总结——blackbox_lite组件#附录：组件分析]]**

### 适配分析

#### LiteOS 接口

##### `LOS_BinarySemCreate` —— 创建二元信号量

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

##### `LOS_SemPend` —— P 操作

```c
UINT32 LOS_SemPend(UINT32 semHandle, UINT32 timeout);
```

| 项 | 说明 |
|---|---|
| 参数 semHandle | 创建时拿到的句柄 |
| 参数 timeout | **毫秒**。三个特殊值：`LOS_NO_WAIT`(0)=非阻塞；`LOS_WAIT_FOREVER`(0xFFFFFFFF)=永久阻塞；N=最多等 N 毫秒 |
| 返回 | LOS_OK 拿到令牌；`LOS_ERRNO_SEM_TIMEOUT` 超时没拿到；其他错误码 |

（`LOS_NO_WAIT`/`LOS_WAIT_FOREVER` 定义于内核 `los_base.h:84/90`。）


##### `LOS_SemPost` —— V 操作

```c
UINT32 LOS_SemPost(UINT32 semHandle);
```

| 项 | 说明 |
|---|---|
| 返回 | LOS_OK；`LOS_ERRNO_SEM_OVERFLOW` = 令牌已满还硬还（二元信号量上重复释放） |


##### `LOS_Msleep` —— 毫秒延时

```c
VOID LOS_Msleep(UINT32 msecs);      /* los_base.h:287 */
```

| 项 | 说明 |
|---|---|
| 参数 | **毫秒数**（M 就是 ms 的意思） |
| 效果 | 当前任务挂起（让出 CPU 去睡觉），时间到再被唤醒 |
| 单位 | **毫秒** ← 记住这个，和 CMSIS 的 osDelay（tick）不同！ |

#### CMSIS-RTOS2 接口

##### `osSemaphoreId_t` —— 信号量句柄类型

```c
typedef struct os_semaphore_def *osSemaphoreId_t;   /* 本质是指针 */
```


##### `osSemaphoreNew` —— 创建信号量

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

##### `osSemaphoreAcquire` —— P 操作（拿令牌）

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



##### `osSemaphoreRelease` —— V 操作（还令牌）

```c
osStatus_t osSemaphoreRelease(osSemaphoreId_t semaphore_id);
```

成功返回 `osOK`；**令牌已满**时返回 `osErrorResource`（对应 LOS 的 SEM_OVERFLOW）。
本组件 4 处释放全部有"同函数内先成功 Acquire"的前置条件，满员释放路径不可达。


##### `osDelay` & `osKernelGetTickFreq`

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

##### `osThreadNew` —— 创建线程

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

**启动前创建线程安全吗？**
安全。树内核的 osThreadNew 底层是 `LOS_TaskCreate`，它在调度器未启动时只是把任务
登记进就绪队列，`osKernelStart()` 后才真正运行——与改造前 pthread_create 的行为完全一致。


#### 适配清单

##### blackbox_core.c

| #   | 位置                  | 原接口                                                    | 新接口                                                                       | 接口说明         | 修改方案                                                                                        |
| --- | ------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------- |
| 1   | :19                 | `#include "pthread.h"`                                 | `#include "cmsis_os2.h"`                                                  | POSIX线程头文件引入 | 头文件替换，pthread.h -> cmsis_os2.h                                                              |
| 2   | :26-28              | LOS_WAIT_FOREVER=0xFFFFFFFF / LOS_NO_WAIT=0 / LOS_OK=0 | osWaitForever / 0U / osOK                                                 | 内核常量复制定义     | 删除 LOS_WAIT_FOREVER / LOS_NO_WAIT / LOS_OK                                                  |
| 3   | :39                 | `static unsigned int g_opsListSem`                     | `static osSemaphoreId_t g_opsListSem`                                     | 信号量句柄类型      | 句柄类型改为CMSIS句柄，unsigned int -> osSemaphoreId_t                                               |
| 4   | :99                 | `LOS_Msleep(LOG_ROOT_DIR_WAIT_TIME)`                   | `osDelay(LOG_ROOT_DIR_WAIT_TIME * osKernelGetTickFreq() / MS_PER_SECOND)` | 毫秒级任务延时      | 原LOS_Msleep参数为毫秒，osDelay参数为tick数，需要按osKernelGetTickFreq()换算，即tick = 毫秒 * 频率 / MS_PER_SECOND |
| 5   | :150 / :214         | `LOS_SemPend(sem, LOS_WAIT_FOREVER) != 0`（2 处）         | `osSemaphoreAcquire(sem, osWaitForever) != osOK`                          | 阻塞等待信号量      |                                                                                             |
| 6   | :261                | `LOS_SemPend(sem, LOS_NO_WAIT) != 0`                   | `osSemaphoreAcquire(sem, 0U) != osOK`                                     | 非阻塞等待信号量     |                                                                                             |
| 7   | :177/:225/:234/:294 | `LOS_SemPost(sem)`（4 处）                                | `osSemaphoreRelease(sem)`                                                 | 释放信号量        |                                                                                             |
| 8   | :314                | `LOS_BinarySemCreate(1, &sem) != LOS_OK`               | `sem = osSemaphoreNew(1, 1, NULL); 判 NULL`                                | 二元信号量创建      |                                                                                             |
| 9   | :320                | `pthread_create(&tid, NULL, SaveErrorLog, NULL)`       | `osThreadNew(SaveErrorLog, NULL, NULL) == NULL`                           | 后台故障日志保存线程创建 |                                                                                             |


##### 公开头与构建

| #   | 位置                           | 原来                      | 现在                                                          | 为什么                                                   |
| --- | ---------------------------- | ----------------------- | ----------------------------------------------------------- | ----------------------------------------------------- |
| 10  | kits/blackbox_adapter.h      | 3 行 LOS_ 内核函数 extern 声明 | 删除                                                          | 公开头只应声明组件自己的 API，内核声明属于接口污染                           |
| 11  | innerkits/blackbox_adapter.h | 同上                      | 删除（与 kits 副本同步）                                             | 两份头文件保持一致                                             |
| 12  | BUILD.gn :26                 | 无 cmsis 头文件路径           | include_dirs 首位新增 `//third_party/cmsis/CMSIS/RTOS2/Include` | 提供 cmsis_os2.h 搜索路径；放首位保证优先命中；不 dep 树内核（预编译内核产品会被误拉入） |
| 13  | bundle.json :26-27           | `"third_party": []`     | `"third_party": ["cmsis"]`                                  | 依赖元数据补全，纯声明无编译影响                                      |


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

### 结论



### 附录：组件分析