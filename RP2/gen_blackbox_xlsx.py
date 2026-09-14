#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 生成 blackbox_lite CMSIS-RTOS2 适配接口改造清单 Excel 表格
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

OUT = "/home/houcq/resource/blackbox_lite_接口改造清单.xlsx"

HEADERS = ["组件", "文件", "原接口（LOS接口）", "新接口（CMSIS接口/POSIX接口）", "接口说明", "修改方案"]

ROWS = [
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "#include \"pthread.h\"",
     "#include \"cmsis_os2.h\"",
     "POSIX 线程头文件引入",
     "头文件替换（blackbox_core.c:19）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "局部兜底宏 LOS_WAIT_FOREVER=0xFFFFFFFF / LOS_NO_WAIT=0 / LOS_OK=0",
     "CMSIS 标准常量 osWaitForever / 0U / osOK",
     "内核常量复制定义（兼容脚手架残留）",
     "删除 3 个局部 #ifndef 兜底宏；新增 BLACKBOX_TASK_STACK_SIZE 0x1000（blackbox_core.c:26-28）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "static unsigned int g_opsListSem（LOS 信号量句柄）",
     "static osSemaphoreId_t g_opsListSem",
     "信号量句柄类型",
     "句柄类型改为 CMSIS 句柄（blackbox_core.c:39）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "LOS_Msleep(1000)",
     "osDelay(1000 * osKernelGetTickFreq() / 1000)",
     "毫秒级任务延时（WaitForLogRootDir）",
     "延时迁移；osDelay 粒度为 tick，按 osKernelGetTickFreq() 换算（1000Hz→1000ticks、100Hz→100ticks，均 1000ms）（blackbox_core.c:99）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "LOS_SemPend(sem, LOS_WAIT_FOREVER)（2 处）",
     "osSemaphoreAcquire(sem, osWaitForever)",
     "阻塞等待信号量（SaveErrorLog 线程 / BBoxRegisterModuleOps）",
     "判错 != 0 改为 != osOK；osWaitForever=0xFFFFFFFFU 与原宏数值一致（blackbox_core.c:150/214）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "LOS_SemPend(sem, LOS_NO_WAIT)（1 处）",
     "osSemaphoreAcquire(sem, 0U)",
     "非阻塞等待信号量（BBoxNotifyError 通知路径）",
     "0 超时严格非阻塞：有令牌返回 osOK，无令牌返回 osErrorTimeout（blackbox_core.c:261）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "LOS_SemPost(sem)（4 处）",
     "osSemaphoreRelease(sem)",
     "释放信号量（各临界区出口）",
     "一一替换；4 处均有同函数内成功 Acquire 前置，无满员再释放路径（blackbox_core.c:177/225/234/294）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "LOS_BinarySemCreate(1, &g_opsListSem) != LOS_OK",
     "g_opsListSem = osSemaphoreNew(1, 1, NULL); 判 NULL",
     "二元信号量创建（BBoxInit）",
     "max_count=1 即二元信号量（树内核实现即映射回 LOS_BinarySemCreate）；成功判定由 != LOS_OK 改为句柄 == NULL（blackbox_core.c:314）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/blackbox_core.c",
     "pthread_create(&taskId, NULL, SaveErrorLog, NULL) != 0",
     "osThreadNew(SaveErrorLog, NULL, &taskAttr) == NULL",
     "后台故障日志保存线程创建（BBoxInit）",
     "SaveErrorLog 签名 void* 改为 void（匹配 osThreadFunc_t，规避 -Wall 告警）；osThreadAttr_t 九字段按位序初始化：name=\"BlackBoxTask\"、stack_size=0x1000、priority=osPriorityNormal(24)（blackbox_core.c:320）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/interfaces/native/kits/blackbox_adapter.h",
     "extern 声明 LOS_BinarySemCreate / LOS_SemPend / LOS_SemPost（3 行）",
     "（删除，无替换）",
     "公开头内核声明污染（非组件 API）",
     "删除 3 行 extern 声明及注释；其余内容不动（原 52 行 → 46 行）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/interfaces/native/innerkits/blackbox_adapter.h",
     "extern 声明 LOS_BinarySemCreate / LOS_SemPend / LOS_SemPost（3 行）",
     "（删除，无替换）",
     "公开头内核声明污染（与 kits 版内容相同，副本同步）",
     "删除 3 行 extern 声明及注释；与 kits 版保持一致（原 52 行 → 46 行）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/BUILD.gn",
     "（无 CMSIS 头文件搜索路径）",
     "include_dirs 首位新增 //third_party/cmsis/CMSIS/RTOS2/Include",
     "构建集成：cmsis_os2.h 搜索路径",
     "组件 include_dirs 先于板级/SDK 目录命中；不新增 //kernel/liteos_m 依赖（预编译内核产品会误拉入树内核）（BUILD.gn:26）"],
    ["blackbox_lite", "base/hiviewdfx/blackbox_lite/bundle.json",
     "\"third_party\": []",
     "\"third_party\": [\"cmsis\"]",
     "第三方依赖元数据",
     "补充 cmsis 依赖（组件名已在 third_party/cmsis/bundle.json 注册；纯元数据无编译影响）（bundle.json:26-27）"],
]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "接口改造清单"

header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="4472C4")
body_font = Font(name="微软雅黑", size=10)
thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap_top = Alignment(wrap_text=True, vertical="top")
center = Alignment(wrap_text=True, vertical="center", horizontal="center")

widths = [14, 40, 40, 44, 26, 46]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

for col, h in enumerate(HEADERS, 1):
    c = ws.cell(row=1, column=col, value=h)
    c.font = header_font
    c.fill = header_fill
    c.alignment = center
    c.border = border
ws.row_dimensions[1].height = 24
ws.freeze_panes = "A2"

for r, row in enumerate(ROWS, 2):
    for col, v in enumerate(row, 1):
        c = ws.cell(row=r, column=col, value=v)
        c.font = body_font
        c.alignment = center if col == 1 else wrap_top
        c.border = border

wb.save(OUT)
print("saved:", OUT, "rows:", len(ROWS))
