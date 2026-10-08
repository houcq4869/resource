
### 需求背景

OpenHarmony解决方案为支持多内核需求，切换内核不影响上层服务&框架功能，需要上层部件统一适配CMSIS&POSIX接口，替代使用操作系统原生接口（比如LOS_xx）。排查中发现blackbox_lite组件使用了LiteOS-M原生接口及pthread接口，需要替换成CMSIS-RTOS2标准接口

### blackbox_lite

#### 组件介绍

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

**具体组件代码介绍见文末**

### 适配分析



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
