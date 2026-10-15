### 需求背景

#### 需求分析

**OpenHarmony解决方案为支持多内核需求，切换内核不影响上层服务&框架功能，需要上层部件统一适配CMSIS&POSIX接口，替代使用操作系统原生接口（比如LOS_xx）。**

**分工规则：**

| 系统类型            | 统一使用                      |
| --------------- | ------------------------- |
| small 系统        | POSIX                     |
| mini 系统         | CMSIS-RTOS2               |
| small+mini 共编组件 | 存在分支隔离则分开适配，没有则共用一套 POSIX |

**blackbox_lite组件接口分析**
- **形态判断**：查 `bundle.json`，`adapted_system_type` 只有 `"mini"`
- 使用了LiteOS-M原生接口（信号量、延时等）及pthread接口（线程），两套混用，需要全部替换成CMSIS-RTOS2标准接口。


**改造目的：组件代码和具体内核解耦**——无论LiteOS-M或者其他RTOS，只要提供CMSIS-RTOS2实现即可

```mermaid
graph TB
    subgraph before["改造前：直连内核"]
        C1["组件代码"] -->|"LOS_* + pthread 混用"| K1["LiteOS-M"]
    end
    subgraph after["改造后：走标准接口层"]
        C2["组件代码"] -->|"osXxx 标准接口"| CMSIS["CMSIS-RTOS2 API"]
        CMSIS --> K2["liteos_m 实现（cmsis_liteos2.c）"]
        CMSIS -.-> K3["其他内核实现<br/>（FreeRTOS / Zephyr / ...）"]
    end
```


#### blackbox_lite组件介绍

**blackbox_lite组件**类似黑匣子：

> **当系统或某个模块发生致命错误（panic、看门狗复位、掉电、系统重启）时，在"倒下"之前，把各个模块的关键现场信息（错误事件、模块名、错误描述、各模块自带的诊断数据）收集、保存下来，供事后分析定位问题。**

**使用场景：**

| 场景                 | 行为                                  |
| ------------------ | ----------------------------------- |
| 内核 panic / 系统看门狗复位 | 复位前把各模块的关键寄存器、状态信息 dump 到日志文件       |
| 掉电 / 异常关机          | 保存最后痕迹                              |
| 某个业务模块检测到自身异常      | 调用黑盒接口记录事件，按需触发模块自检（Dump）或重启（Reset） |

**组件逻辑：**

```mermaid
graph LR
    MOD["业务模块<br/>（wifi / 安全 / ...）"] -->|"① 注册"| REG["注册表 g_opsList<br/>（双向链表）"]
    ERR["错误发生者"] -->|"② 通知"| DIST["通知分发<br/>按模块名调回调"]
    SAVE["后台保存线程<br/>SaveErrorLog"]
    REG --> SEM["二元信号量<br/>g_opsListSem"]
    DIST --> SEM
    SAVE --> SEM
    DIST --> ADP["平台适配层<br/>7 个弱符号接口"]
    SAVE --> ADP
```

- **注册**：模块想被黑盒"照顾"，先来登记，带上4个诊断回调（Dump / Reset / GetLastLogInfo / SaveLastLog）；
- **通知**：出错 ->  `BBoxNotifyError`，黑盒按模块名找到节点，调它登记时留下的回调；
- **后台保存**：一个一次性线程，启动后把各模块的日志收走存盘上传；
- **锁**：三条路径都碰同一个注册链表，用**一个二元信号量**做互斥。

平台相关的动作（写文件、取日志路径、重启系统……）全部做成**弱符号接口**下沉到适配层——黑盒只管逻辑，怎么落盘平台自己说了算。

这也是本次改造一个关键的观察：**内核接口全部集中在 `blackbox_core.c` 一个源文件里，适配层根本不碰内核**——改动面天然收敛。

数据结构、启动时序、运行场景的细节见文末[[#附录：组件分析]]。

### 适配思路

先给结论：**这类改造的难点不在"怎么改"，而在"怎么证明改了跟没改一样"。** 接口替换本身是体力活，真正花功夫的是逐条论证语义等价和时序安全。

整体思路五步：

```mermaid
flowchart LR
    A["定范围<br/>mini-only？"] --> B["摸家底<br/>盘点内核接口调用点"]
    B --> C["建映射<br/>接口一对一施工图"]
    C --> D["辨差异<br/>真正要动脑的少数点"]
    D --> E["保等价<br/>语义 + 时序逐条论证"]
    E --> F["验证：编译 / 符号 / 头文件命中"]
```

#### ① 定范围：判断改造形态

见上文——mini-only，单套CMSIS，无分支。**这一步放在最前面**，因为它直接决定后续所有动作的复杂度；如果当初判断错（比如其实有small共编），后面全部返工。

#### ② 摸家底：盘点调用点

全仓grep内核接口，结果**全部集中在 blackbox_core.c**：

| 类别 | 接口 | 处数 |
|---|---|---|
| 信号量创建 | `LOS_BinarySemCreate` | 1 |
| 信号量等待 | `LOS_SemPend`（阻塞×2、非阻塞×1） | 3 |
| 信号量释放 | `LOS_SemPost` | 4 |
| 延时 | `LOS_Msleep` | 1 |
| 线程创建 | `pthread_create` | 1 |
| 头文件/兜底宏 | `pthread.h`、局部LOS常量定义 | 2 |

另外两处"藏得深"的也要翻出来：两份公开头里抄的3行LOS函数声明（接口污染），以及bundle.json里缺失的第三方依赖声明。**盘点宁可多花十分钟，也不要改到一半发现漏了一处。**

#### ③ 建映射：一张表当施工图

6组接口一对一，先列总表再动手：

| 原接口 | 新接口 | 功能 |
|---|---|---|
| `LOS_BinarySemCreate(1, &sem)` | `osSemaphoreNew(1, 1, NULL)` | 创建二元信号量 |
| `LOS_SemPend(sem, LOS_WAIT_FOREVER)` | `osSemaphoreAcquire(sem, osWaitForever)` | 阻塞拿令牌 |
| `LOS_SemPend(sem, LOS_NO_WAIT)` | `osSemaphoreAcquire(sem, 0U)` | 非阻塞拿令牌 |
| `LOS_SemPost(sem)` | `osSemaphoreRelease(sem)` | 还令牌 |
| `LOS_Msleep(ms)` | `osDelay(ms * osKernelGetTickFreq() / 1000)` | 延时 |
| `pthread_create(&tid, NULL, fn, NULL)` | `osThreadNew(fn, NULL, &attr)` | 创建线程 |

替换前先确认过几个"宽心点"，不是拍脑袋就换：

- `osSemaphoreNew` 的 max_count=1 就是二元信号量，而且树内核实现里 max==1 时底层**就是** `LOS_BinarySemCreate`——不是"功能相似"，是同一个内核对象；
- `osWaitForever`（0xFFFFFFFF）和 `LOS_WAIT_FOREVER` 数值一模一样，常数只是从内核头文件搬到了标准头；
- `osOK` 就是0，判错写法 `!= osOK` 和原来的 `!= 0` 完全等价。

#### ④ 辨差异：真正要动脑的只有三处

映射表大部分是机械替换，但有三处不能无脑改——**这三处才是本次改造的核心知识点**：

**1. `osDelay` 的单位是tick，不是毫秒（唯一的"算法级"改动）**

`LOS_Msleep` 传毫秒，`osDelay` 传tick数。同样想延时1秒：

| 接口 | 单位 | 1000Hz内核（WS63） | 100Hz内核 |
|---|---|---|---|
| `LOS_Msleep` | 毫秒 | 传1000 | 传1000（内核自动换算） |
| `osDelay` | **tick** | 传1000 | **传100**（不换算就差10倍） |

所以必须按内核频率换算：

```
tick 数 = 毫秒数 × osKernelGetTickFreq() / 1000
```

频率**现场查询、不写死**——组件才能在1000Hz和100Hz的产品上都精确延时。这是整个改造里最容易踩的坑：在WS63上直接把1000传给osDelay"碰巧是对的"，换到别的产品就错10倍，而且没有任何编译期报错。

**2. 句柄风格：出参式 → 返回值式**

LOS是"返回错误码 + 指针出参写句柄"，CMSIS是"直接返回句柄，NULL判失败"。两种风格无优劣，改代码时把判定从 `!= LOS_OK` 换成 `== NULL` 即可，语义完全一致。

**3. 线程函数签名**

CMSIS规定线程函数签名必须是 `void func(void *)`，原 `SaveErrorLog` 是 `void* func(void *)`——不改会触发编译告警。顺手把原来pthread传NULL的"全默认属性"显式化成 `osThreadAttr_t`（线程名 BlackBoxTask / 栈 0x1000 / 优先级 osPriorityNormal），取值都对齐LiteOS默认，行为不变、可读性更好。

#### ⑤ 保等价：两个"敢不敢"的问题

黑盒的初始化跑在 **CORE_INIT阶段——调度器还没启动**。有两个时序问题必须提前论证，不能等跑飞了再查：

- **启动前创建信号量/线程，敢不敢？** 敢。`osThreadNew` 底层是 `LOS_TaskCreate`，调度器没转起来时只是把任务登记进就绪队列，`osKernelStart()` 之后才真正运行——与原来 `pthread_create` 的行为完全一致；
- **启动前调 `osDelay` 会怎样？** 树内核里会退化成空转桩。但本组件的 `osDelay` 只出现在运行时路径（错误通知、后台线程体），CORE_INIT钩子里没人调它，不受影响。

#### 顺手清理的三件事

适配主线之外，三件"早就该做"的清理一并完成：

| 事项 | 内容 | 理由 |
|---|---|---|
| 公开头去污染 | kits/innerkits两份 `blackbox_adapter.h` 删3行LOS extern声明 | 公开头只该声明组件自己的API；全树核查过无人使用 |
| 兜底宏退场 | 删局部 `#define LOS_WAIT_FOREVER ...` 一组复制品 | 内核常量复制品随LOS接口一并退场，改用标准常量 |
| 构建接线 | BUILD.gn include_dirs **首位**加 `//third_party/cmsis/CMSIS/RTOS2/Include`；bundle.json 补 `third_party: ["cmsis"]` | 首位保证优先命中标准头；**刻意不dep树内核**——nearlink_dk_3863用预编译内核，dep树内核目标会把整棵内核误拉进构建 |

### 改动面一览

5个文件、13处改动，**业务逻辑零变化**，对外API（`BBoxRegisterModuleOps` / `BBoxNotifyError` / `struct ModuleOps`）零变化——下游无感知：

| 文件 | 改动 | 性质 |
|---|---|---|
| `blackbox_core.c` | 9处接口替换 + 线程签名调整 | 唯一动逻辑的文件（333行→323行） |
| kits / innerkits `blackbox_adapter.h` | 各删3行LOS声明 | 接口清理 |
| `BUILD.gn` | +1行include | 构建接线 |
| `bundle.json` | 补cmsis依赖 | 纯元数据声明 |

### 怎么证明改对了

编译通过只是底线，这次做了三层验证：

1. **编译**：nearlink_dk_3863（WS63预编译内核产品）build success；
2. **符号**：nm扫描 `libblackbox_lite.a`——`los_` 前缀残留 **0个**；6个os\*符号全部为U（未定义，待内核解析），且预编译内核的固件符号清单里**提前**核实过这6个符号都存在；
3. **头文件命中**：重生成的ninja里 `-I third_party/cmsis` 排在SDK各cmsis副本之前，`cmsis_os2.h` 命中符合预期。

行为层面另有5条等价性论证（信号量同底、P/V同义、延时更准、线程同行为、错误路径逐条保留），评审时逐条过。**"纯接口替换"类改造，等价性是论证出来的，不是测出来的**——这算是一条方法论。

### 结论

[OH master分支PR](https://gitcode.com/openharmony/hiviewdfx_blackbox_lite/pull/28)
[OH 6.1 LTS分支PR](https://gitcode.com/openharmony/hiviewdfx_blackbox_lite/pull/29)

**一句话总结**：mini-only组件的CMSIS适配 = 定范围（单套实现）→ 摸家底（调用点全集中在一个文件）→ 建映射（6组一对一）→ 盯住三处真差异（tick单位/句柄风格/线程签名）→ 论证时序安全 → 符号级验证。真正需要动脑的环节不到两成，剩下的是严谨的体力活。

### 附录：组件分析

#### 数据结构三件

| 结构 | 角色 | 内容 |
|---|---|---|
| `struct ErrorInfo` | 一张"事故报告单" | event / module / errorDesc 三字段 |
| `struct ModuleOps` | 模块的"诊断能力"登记表 | 模块名 + Dump / Reset / GetLastLogInfo / SaveLastLog 四个回调（可NULL） |
| `struct BBoxOps` | 注册表节点 | 链表节点 + ModuleOps |

#### 启动时序

```mermaid
sequenceDiagram
    participant U as 上电
    U->>U: osKernelInitialize()
    U->>U: OHOS_SystemInit() 遍历 CORE_INIT
    U->>B: BBoxInit（优先级 1）
    Note over B: 创建信号量（令牌 1）<br/>创建 SaveErrorLog 线程——只入队，还没跑
    U->>B: BBoxAdapterInit（优先级 2）
    Note over B: 注册 SYSTEM 模块<br/>拿令牌立即成功（令牌现成）
    U->>U: osKernelStart()
    Note over B: 调度器转起来，SaveErrorLog 这才真正开跑
```

"创建不执行"是理解启动时序的关键：线程创建本质是"登记进就绪队列"，调度器启动前登记了也不会跑。这也是前文"启动前创建线程敢不敢"的答案来源。

#### 三个运行场景

```mermaid
flowchart TD
    N["BBoxNotifyError"] --> Q{"needSysReset?"}
    Q -->|"= 0 温和路径"| W["等文件系统 1000ms"]
    W --> T["非阻塞拿锁"]
    T -->|"拿到"| F["按模块名找节点"]
    T -->|"没拿到"| G["打日志，放弃本次上报"]
    Q -->|"≠ 0 致命路径"| F2["不等、不拿锁<br/>直接找节点"]
    F --> D["Dump / Reset 回调<br/>都没注册则默认落盘"]
    F2 --> D2["Dump / Reset 回调"]
    D2 --> R["RebootSystem 复位"]
```

重点体会**三种锁策略的设计意图**：

| 路径 | 拿锁方式 | 为什么 |
|---|---|---|
| 注册 | 阻塞（osWaitForever） | 注册方"不成功不罢休"，值得等 |
| 后台保存 | 阻塞 | 专职干活，排队就好 |
| 错误通知（温和） | 非阻塞（0超时） | 报错的人不能被锁卡住排队——宁丢一次上报，不堵死报错者 |
| 错误通知（致命） | 不拿锁 | 系统马上要复位，抢时间保现场第一，锁破坏了也无所谓，有意取舍 |

#### 文件地图

| 文件 | 职责一句话 |
|---|---|
| `blackbox_core.c` | 核心逻辑：注册表、通知分发、后台保存线程（本次改造唯一动逻辑的文件） |
| `blackbox_adapter.c` | 平台适配层：7个弱符号接口默认实现 + 启动注册SYSTEM模块 |
| `blackbox_detector.c/.h` | 事件上传桩（预留接口） |
| `interfaces/native/kits/blackbox.h` | 对外API + 数据结构 |
| `interfaces/native/{kits,innerkits}/blackbox_adapter.h` | 平台接口声明（两份副本同步维护） |
| `BUILD.gn` / `bundle.json` | 构建脚本 / 组件元数据 |
