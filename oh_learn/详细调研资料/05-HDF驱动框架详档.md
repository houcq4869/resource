# 详档 · HDF 架构/驱动加载/HCS/HDI/平台驱动/海思实证

> 来源：OpenHarmony 深度调研（ulw-research 会话 20261102-105649）
> Worker：W5 (librarian, bg_d4eebd19) · 耗时 9m31s · 采集/访问日期：2026-11-02
> 对应主报告《OpenHarmony调研报告.md》章节：第 6 章
> 性质：worker 原始调研产出（仅清理 harness 包装，未做二次编辑）；关键结论已多源交叉核验后并入主报告。备注：基于 drivers_hdf_core 本地克隆的源码级行号证据；含 .drv 纠错、Linux 适配器逐文件分析

---

我将系统地调研 OpenHarmony HDF。先从核心文档来源和代码仓库着手。

The docs index is available. Let's fetch key pages: driver-overview-foundation.md, driver-hdf-manage.md, and the HDF driver model docs. Also drivers_hdf_core README.

Let me fetch in parallel.

文档索引已确认。现在开始拉取核心文档页和仓库结构。

Excellent primary source. Now read manage.md (42KB) — that's the HDF driver development flow doc, key for .hcs, .drv, host, DeviceNode, boot flow.

Let me read it.

核心概述已获取，现在阅读 HDF 开发流程的详细文档：

Continue reading manage.md for driver implementation (HdfDriverEntry, .drv? Actually .drv file is the compiled driver? Let me check). Continue.

Continue reading the driver implementation and configuration sections (hdf_driver_register, .drv file mention).

Great. Now I need:
- .drv file extension — actually in HDF, kernel driver modules are compiled to .ko (Linux) or .drv (LiteOS) files? In HDF, the "driver extension model" — I recall HDF has a "driver extension" mechanism where a driver can be compiled as a dynamic module (.drv) loaded at runtime on LiteOS. Let me search docs for ".drv".
- HDF boot flow: hdf_devmgr / device host parsing hcs.
- HDI & hdi-gen.
- Linux side binding (khdf, lhdf: linux hdf).
- drivers_hdf_core repo structure.

Let me do parallel: grep repo README, docs for .drv, and the repo tree.

Use gitee API to list drivers_hdf_core tree? Gitee API: https://gitee.com/api/v5/repos/openharmony/drivers_hdf_core/git/trees/master?recursive=1 maybe. Let's try.

Also websearch queries needed (at least 8). Let's plan queries:
1. "OpenHarmony HDF 驱动框架 hcs hdi-gen"
2. "OpenHarmony HDF .drv 驱动扩展"
3. "OpenHarmony lhdf Linux HDF 驱动"
4. "drivers_hdf_core framework adapter khdf"
5. "OpenHarmony HDF platform driver 适配 SoC HiSilicon"
6. "OpenHarmony driver-hdf-development HDI"
7. "HDF device host hdf_devmgr boot flow"
8. "OpenHarmony HDF vs Linux device driver device tree"

Let me first fetch repo README and tree, plus grep docs for .drv.

Gitee API may need different call (no ?recursive maybe). Let's check tree.json content. Probably an error message "Not Found". Let me try the API v5 with proper endpoint, else clone the repo shallow via git (gitee). Cloning drivers_hdf_core may be big (~?), but shallow depth 1 should be fine (maybe 100MB). Let's try gitee api first with access_token not needed for public but rate limited.

Actually simpler: git clone --depth 1 https://gitee.com/openharmony/drivers_hdf_core.git — good for exact structure. Let's do it in background maybe. Meanwhile do websearch queries.

Repo cloned. Let's inspect structure and gather facts: platform drivers, .drv files, hdi-gen, hcs, khdf adapter, i2c, gpio, etc.

Also start websearches in parallel. Let me do multiple websearch calls with varied queries.

Good. Now let's inspect the cloned repo deeply for structure, .drv, platform driver dirs, adapter/khdf, hdi-gen, hcs samples, and .drv file handling.

Also need to search for the .drv extension mechanism. Let me grep in repo for ".drv".

Interesting — no ".drv" extension in current master. The ".drv" driver extension model may be from older HDF docs or the "driver extension" concept: HDF driver can be compiled as .drv in LiteOS? Let me check docs for "驱动扩展" or ".drv". Search the docs repo. We can clone docs? big. Use grep on gitee? Let's fetch the HDF driver usage doc "driver-hdf-development.md" maybe mentions driver extension (.drv). Also there's the old hdf "driver sample" doc.

Actually I recall: In HDF's LiteOS-M, drivers are compiled into the kernel image; in LiteOS-A, drivers may be built as .drv dynamic modules? Hmm. In OpenHarmony early versions (3.0), "驱动扩展" via .drv: The HDF framework supports "driver extension" where each driver compiled as a .drv file loaded by the framework at boot, used on LiteOS-A? Let me search.

Let me run websearch for "HDF .drv 文件 驱动" and "HDF 驱动扩展 模型 .drv".

Also check the repo for "drv" loaders: grep for "dlopen", "HdfDriverLoader", "GetDriverEntry".

Let me also inspect framework/core structure: host, manager, shared, adapter, common.

Key: driver loading is via .hdf.driver section + dynamic .so loading. The ".drv" extension isn't in current repo. Need to verify what ".drv" refers to. Historically OpenHarmony HDF build produced `xxx.drv` for LiteOS-A user-mode? Hmm, in LiteOS-M, .drv? Let's search specifically "hdf .drv" "moduleName .drv" "libhdf_platform.z.so".

Actually there IS ".drv" in the build system: In OpenHarmony, hdf drivers are built as "drivers" into a `.drv` file? Let me recall build templates: `hdf_driver("xxx")` in build/lite produces `libxxx.a`? For LiteOS-A, HDF drivers might be compiled as shared library with extension `.so`. In OpenHarmony LiteOS-A user mode, `uhdf`; kernel `khdf`.

I recall in older OpenHarmony (1.x/2.0) docs: 驱动开发 "编译生成的驱动文件以.drv为后缀"? Hmm. Let me search with a targeted query and also grep the build repo (build_lite / hdf.gni).

Let's fetch hdf.gni from adapter/khdf/liteos.

Now let's get precise source facts from cloned repo. Key files:
- framework/core/host/src/hdf_driver_loader.c (static/dynamic loading, .so, .drv?)
- framework/core/manager/src/devmgr_service.c (boot, hcs parse, host attach)
- framework/core/host/src/hdf_device_node.c
- framework/core/shared (hcs parser)
- framework/tools/hdi-gen
- framework/support/platform/src/fwk (platform manager, platform device)
- adapter/platform/{gpio,i2c,...} — this is key! "adapter/platform" contains platform adapters (SoC-agnostic? Actually adapter/platform contains the Linux kernel platform driver adapters that convert HDF platform APIs to Linux APIs? Let's check).
- adapter/khdf/linux — Linux HDF (khdf) integration including linux driver binding (platform device, device tree).

Let's inspect.

Excellent. adapter/platform contains vendor-specific bare-metal adapters (asr, bes, gr5xx, stm32f4xx, wm) for LiteOS-M. adapter/khdf/linux/platform contains Linux-side platform adapters that implement HDF platform APIs using Linux kernel APIs.

Now inspect hdf_platform.c / platform fwk (platform_manager.c, platform_device.c), and a specific linux adapter e.g. gpio.

Also the "devmgr_service.c" boot flow and "hdf_device_node.c" publish.

Let's read.

Great evidence: Linux GPIO adapter wraps Linux gpiolib (gpio_set_value_cansleep). Good for "HDF drivers coexist with Linux drivers" and "SoC vendor provides adapters".

Now check the Linux platform Makefile/Kconfig to see how adapters are compiled and whether they are selected by kernel config. Also check adapter/khdf/linux/README_zh.md.

Also check how HDF obtains device resources from device tree: "device_resource_if.h" and "hdf_driver_installer"? In Linux, HDF parses device tree? Actually khdf uses HCS + also "hdf_devmgr" parses hcs; the DeviceResourceIf (device_resource_if.h) may parse .hcs only. But patch_hdf.sh integrates into kernel.

Let me check adapter/khdf/linux/README_zh.md and Makefile.

Great — Kconfig shows "PWM_HI35XX" (HiSilicon Hi35xx) evidence of a vendor platform adapter. Let's see the rest and the pwm dir for hi35xx.

Also check hcs config in a vendor: vendor/hihope/rk3568/hdf_config/khdf. We can fetch from gitee raw. Key: device_info.hcs, hdf.hcs, and per-driver config.

Let's inspect more: adapter/khdf/linux/platform/pwm, and board config samples in repo (framework/sample). Also framework/sample has hcs sample.

Then read devmgr_service.c boot flow (DeviceManagerInit late_initcall). And hdf_device_node.c.

Also HDI: drivers/interface repo (IDL), hdi-gen tool. And "uhdf2" for user-mode drivers.

Let me gather in parallel.

Excellent — concrete HiSilicon hi35xx Linux PWM driver using Linux pwm_chip and device tree probe. Interesting: this bypasses HDF platform framework, registering native Linux PWM.

Now let's inspect Linux i2c adapter to see whether it uses i2c_transfer, and whether HDF drivers use Linux device tree. Also check "device_resource_if.h" and "hdf_devmgr" hcs parse. And how HDF device gets resource from HCS vs device tree: In OpenHarmony standard system, HDF config is in vendor/.../hdf_config/khdf. The HDF devices are defined solely in HCS, not DT. Linux drivers in kernel still use DT. But HDF has "hdf_driver_installer" possibly for installing native Linux drivers into HDF? Let's inspect adapter/khdf/linux/model or "hdf_linux_driver" bridging.

Also there's "framework/core/manager/src/hdf_driver_installer.c" — let's read it. And adapter/khdf/linux/manager/src/sym_export.c.

Also "hdf_load_vdi.c" in host — VDI = vendor device interface? Let's check.

Then HDI: framework/tools/hdi-gen README, drivers/interface repo (IDL), uhdf2 (user-mode HDF). 

Also hcs config for a real board: vendor/hihope/rk3568/hdf_config/khdf/device_info.hcs. Let's fetch that raw. And maybe vendor/hisilicon? HiSilicon Hi3516 vendor dir: vendor/hisilicon/hispark_taurus/hdf_config/... Let me fetch.

Let me batch.

So Linux i2c adapter calls i2c_transfer on an i2c_adapter obtained from ... let's see how cntlr->priv is set (probably via i2c_get_adapter with bus number). Let's view relevant code. Also check gpio adapter's bind (LinuxGpioBind) to see how it creates GpioCntlr and uses gpio base, "device_resource" from HCS.

Let me look at gpio adapter bottom, and i2c adapter.

Good. Now HDI. Need to fetch:
- framework/tools/hdi-gen README (what it does: generates C/C++ stubs from .idl)
- drivers/interface repo structure (IDL files, e.g., display/...)
- uhdf2 adapter (user-mode HDF, host process, dlopen "libxxx.z.so")

Also HCS hierarchical config "hdf.hcs" entry, and vendor config layouts. Fetch vendor/hihope/rk3568/hdf_config/khdf/device_info.hcs and hdf.hcs. And HiSilicon vendor maybe.

Let's check hdi-gen README and uhdf2.

drivers_interface repo may be different: openharmony/drivers_interface exists? Actually repo name is "drivers_interface" (yes). README might be README.md only. Let me check via gitee page or git ls-remote. Or maybe repo is "drivers_interface" under openharmony — the URL raw may have failed because of path. Try README.md.

Also hdi-gen README missing; check main.cpp usage or docs "driver-hdf-using-hdi". There's a doc "HDI接口开发" maybe in docs: driver-hdf-development.md? Let me list docs dir via gitee API not available; use git clone docs? Docs repo is large (~500MB). Instead fetch directory listing HTML.

Actually there's a known doc: zh-cn/device-dev/driver/driver-hdf-manage.md; and "driver-hdf-faq.md"; plus "driver-hdf-development.md"? The HDI generation docs may be in "zh-cn/device-dev/driver/driver-hdi-*.md"? Let me check the docs Readme listing only showed driver usage. HDI docs might be under "zh-cn/device-dev/driver/driver-hdi.md"?

Let me use gitee's tree page HTML or try raw paths.

Also need docs on "hdf_devmgr" boot flow and "hcs" config in vendor. Let's fetch vendor hihope rk3568 hdf config.

Batch:
1. curl drivers_interface README.md
2. curl vendor/hihope/rk3568/hdf_config/khdf/device_info.hcs (path guess) — check repo tree via git ls-remote? Better clone vendor_hihope shallow? vendor repo may be huge. Use raw fetch attempts.
3. Search docs for "hdi-gen" via gitcode search or google.

Let me also check hdi-gen usage in main.cpp.

Now the remaining big pieces:

1. HDI relationship to HDF: HDI is the interface layer; HDI services are implemented as user-mode HDF drivers (uhdf2), loaded via dlopen of .z.so, and hdi-gen generates proxy/stub from .idl.

2. Boot flow details: DeviceManagerStart → parse hcs → attach hosts → load drivers. Need source evidence in devmgr_service.c: functions like DeviceManagerStart, DevMgrServiceStartService, HdfAttributeManagerGetHostList, DevHostServiceClntInstallDriver.

3. HCS hierarchical config: "hdf.hcs" includes device_info + per-device config; also "hdf_config/khdf" vs "hdf_config/uhdf". Need vendor sample. Let's fetch vendor hihope rk3568.

4. SoC porting conventions: vendor dirs, e.g., device/board/hihope/rk3568, vendor/hihope/rk3568/hdf_config/khdf. HiSilicon: vendor/hisilicon/hispark_taurus/hdf_config. Also drivers/peripheral for device drivers; drivers/interface for HDI IDL.

5. Relationship to native Linux drivers: adapter/khdf/linux integrates HDF into Linux kernel; "lhdf"? Maybe "lhdf" refers to "linux hdf" dir in older repos (drivers/adapter/khdf/linux). Also "linux-side binding": HDF platform adapters wrap native Linux subsystems, while native Linux drivers remain under kernel/linux. There's "patch_hdf.sh" that patches kernel tree to build HDF. Let's read patch_hdf.sh and check "hdf_linux" config. Also check "CONFIG_DRIVERS_HDF" in kernel.

6. Device tree: HDF normally uses HCS, but some adapters use Linux device tree (pwm_hi35xx uses of_platform, i2c adapter enumerates i2c_adapter via bus). Let's verify whether HDF reads DT. Search repo for "of_" usage and "device_node" parse. Also in "adapter/khdf/linux/platform/mipi_dsi/mipi_drm_imx8mm.c" likely uses DT.

Also "hdf_config/khdf/device_info.hcs" includes "hdf.hcs" entry. Let's fetch vendor rk3568 config list.

Let's do parallel fetches. Gitee raw path: https://gitee.com/openharmony/vendor_hihope/raw/master/rk3568/hdf_config/khdf/device_info.hcs
Also hdf.hcs.

And hisilicon: https://gitee.com/openharmony/vendor_hisilicon/raw/master/hispark_taurus/hdf_config/khdf/device_info.hcs

Try.

device_info.hcs path differs. Let's list the rk3568 hdf_config/khdf tree via gitee API? Rate-limited. Alternative: clone vendor_hihope shallow (may be large but let's try with filter=blob:none? gitee supports partial clone? maybe). Simpler: use gitcode mirror raw? Or use gitee page HTML.

Let's try gitee "tree" web page and parse hrefs, or use git ls-tree via clone with sparse checkout.

Try: git clone --depth 1 --filter=blob:none --sparse https://gitee.com/openharmony/vendor_hihope.git — might work.

Also hisilicon path may be hisilicon/hispark_taurus/... Actually vendor repo may be "vendor_hisilicon" with board "hispark_taurus". Let me just fetch gitee page.

Meanwhile read devmgr_service.c around 280-460.

Great. Now read rk3568 device_info.hcs and a platform config (uart), to show vendor-level config conventions and moduleName mapping to .so.

Also fetch HiSilicon vendor config (maybe vendor_hisilicon/hispark_taurus/...). Let's sparse clone vendor_hisilicon / list tree.

Read device_info.hcs now.

Excellent. Note in rk3568, Linux UART uses "driver_name = ttyS" and num — meaning HDF UART adapter maps to native Linux tty. That's a good evidence of coexistence with native Linux drivers.

Let's check the Linux uart adapter for how it uses tty (uart_adapter.c). And also platform uart core.

Also the hdf.hcs boot flow: "hdf.hcs" is the entry include; device_info + per-device configs. HCS parser in framework/core/shared? Let's find HcsParser / DeviceResourceIf.

Next: HiSilicon. Search for vendor hisilicon hdf_config. Try sparse clone vendor_hisilicon. Also "device/board/hisilicon/hispark_taurus" perhaps.

Let's check repo list: vendor_hisilicon might contain "hispark_taurus" or "hispark_pegasus". Let's clone sparse and list top dirs.

Also need "drivers/peripheral" structure to describe peripheral drivers and HDI implementations: repos drivers_peripheral (HAL), drivers_interface (IDL). Let's fetch drivers_peripheral README.

Also HDF "driver model" of "misc" including "dsoftbus, light, vibrator".

And "hdf_dev_eco_tool" (DevEco driver tool), "hcs-view".

Let me batch.

HiSilicon vendor boards. Let's sparse checkout hispark_taurus/hdf_config and hispark_taurus_linux/hdf_config.

Also inspect uart adapter in Linux more: it uses driver_name "ttyAMA" default, opens tty device? Let's read around 500-620.

Then look at HiSilicon HDF config.

Good: Linux UART adapter reads "driver_name" (ttyAMA default) + "num" from HCS, then opens /dev/ttyAMAx? Let's confirm usage of g_driverName — probably snprintf "/dev/%s%d".

Now HiSilicon hdf.hcs and device_info. Read hispark_taurus_linux/hdf_config/hdf.hcs, device_info.hcs (partial).

Also check if there is a "HiSilicon platform adapter" in vendor dir, e.g., vendor/hisilicon/hispark_taurus/hdf_config + drivers/peripheral. HDF platform adapters for Hi3516 live in adapter/khdf/linux/platform (pwm_hi35xx, maybe uart hi35xx?). Let's grep for hi35 in adapter.

Also check "device/board/hisilicon/hispark_taurus" kernel drivers. But porting perspective: SoC vendor provides:
- kernel drivers under kernel/linux/linux-5.10/drivers/... (or vendor kernel patches)
- HDF platform adapters (adapter/khdf/linux/platform/*) if the SoC needs custom (e.g., hi35xx pwm)
- peripheral drivers under drivers/peripheral (audio, display, camera, etc.) and HDI impl
- hdf_config/khdf/*.hcs + uhdf device_info.hcs
- HDI interface IDL under drivers/interface

Let's inspect hdf.hcs from hisilicon.

Excellent. Hi35xx vendor naming: "hisilicon,hi35xx_chip", module names "HDF_PLATFORM_UART", config includes "hisilicon_hi35xx_uart_0".

Now, need to clarify HDI/hdi-gen docs. Let's find official docs about HDI development. Search docs repo file list. Maybe "zh-cn/device-dev/driver/driver-hdf-using-hdi.md" or "driver-hdi-development.md". Use gitee search or webfetch of docs tree HTML? Let's try known docs paths quickly with curl HEAD.

Candidate paths:
- driver-hdf-development.md
- driver-hdf-using-hdi.md
- driver-hdi.md
- driver-hdi-development.md
- driver-hdi-gen.md

Let me test several via curl -o /dev/null -w codes.

Also search web for "hdi-gen HDF 接口生成工具".

Also "driver-hdf-manage.md" mentions "hdf-gen"? The tools include "hdf-gen" (driver code generation?), "idl-gen". hdi-gen generates C/C++ code from .idl. There's also "hdf_dev_eco_tool" (DevEco Studio plugin).

Let's check.

The AGENT.md in drivers_hdf_core is a goldmine (though possibly AI-generated doc in repo? It's in the repo at a specific commit; may be a recent addition — I should be careful; it's primary-ish but I'd rely on code). It confirms hdf_devmgr process, libhdf_host, libhdi, libhdf_platform, Manager-Host multi-process model.

Note: docs repo now lacks HDI doc because docs reorganized? The drivers_interface README is official enough.

Now, remaining gaps:
1. Official doc for HDF "平台驱动适配" (how to implement platform adapter) — driver-platform-*-develop.md, e.g., gpio develop doc describes "GpioCntlrMethod" and adaptation. Fetch one (i2c develop) to cite the unified platform driver API and adapter implementer interface.
2. HDF driver message mechanism (already in manage.md).
3. HDF "driver extension model (.drv)" — still unresolved. The task explicitly mentions ".drv file". I need to determine the truth: In OpenHarmony, kernel driver modules on LiteOS are compiled into `libxxx.a` linked into kernel, or on Linux `.ko`. User-mode drivers are `.z.so`. Is there a `.drv`? Historically, OpenHarmony HDF on LiteOS-A used `.drv`? Let me search code for "drv" suffix in build templates: "hdf_driver" template uses kernel_module. Search build repo for ".drv".

Maybe the ".drv" refers to "驱动扩展能力" in OpenHarmony 4.0 "HDF驱动扩展" — "driver extension" is a mechanism to load third-party drivers from /vendor/etc? Hmm.

Let me search web specifically: "OpenHarmony .drv 驱动" and "hdf drv 文件后缀". Also check docs repo for "drv" via gitcode search? Could clone docs with sparse filter (docs repo huge but blob:none + sparse of driver dir is fine). That's valuable: get exact doc set and grep for "drv". Let's do sparse clone docs/zh-cn/device-dev/driver + readme.

Actually docs repo may be large but blob:none sparse should be quick-ish. Let's try.

Interesting: the last search result (liangkz led_ctrl) has a "drv" folder. That's likely the HDF "driver extension" sample: chapter 9 of "沉浸式剖析OpenHarmony源代码" uses a `.drv` dynamic driver. Let me investigate that repo: gitee.com/liangkzgitee/led_ctrl, folder "drv". Fetch README and drv contents.

This may clarify ".drv" model: In OpenHarmony LiteOS-A, HDF drivers can be compiled into `.drv` files (a driver package?) loaded by hdf_devhost? Let's look.

Also docs folder is available locally now; grep for "drv" in docs/zh-cn/device-dev/driver.

The led_ctrl README has a drv/ dir probably containing "libled_driver.so"? Let's fetch the repo tree. Use git clone shallow.

Also, let's look at the "hdf_dev_eco_tool" (driver extension?). Let's search the repo for "drv" extension in build files from build_lite? Hard.

Let's clone led_ctrl and inspect drv folder + README section about "drv".

The "drv/" folder in led_ctrl is just the driver source folder, not .drv file extension. So the ".drv" in the task's prompt may be a misconception, OR refers to the "driver extension" model in OpenHarmony "HDF驱动扩展" where a driver is packaged as `.drv` (I still recall something like "hdf_driver" package). Let me verify definitively by searching build repo for ".drv" and OpenHarmony docs. Since docs don't mention .drv at all (grep found none), and repo has no ".drv" extension, I should report: no `.drv` file format in current HDF; the "driver extension model" is the HdfDriverEntry + dynamic loading of .so (user mode) / static section (kernel), and "driver extension" in the sense of "扩展驱动" (third-party vendor drivers) is deployed via hdf_config + .z.so. But wait — maybe on LiteOS-A, kernel modules are `.drv`? Let me search "liteos .drv" "hdf drv ko".

Search in gitee code search is hard. Let's grep build repo (build_lite) for "drv". Could clone build_lite sparse. Also "hdf_driver" template output extension. In hdf.gni kernel_module likely outputs .a/.o. Let's read rest of hdf.gni (kernel_module from kernel/liteos_a/liteos.gni). That will show output.

Also check "adapter/khdf/liteos/hdf_driver.mk" for "MODULE_NAME" and output .a.

Let me check hdf_driver.mk and lite.mk.

Then also search web "OpenHarmony HDF .drv" with quotes gave nothing useful except led_ctrl. I think .drv is a red herring; but there IS a concept "驱动扩展" = "driver extension" in HDF: In docs "driver-hdf-manage.md" section "驱动扩展"? Not present. However in OpenHarmony 4.0 there's "HDF驱动扩展能力: 支持驱动插件化" maybe.

Let me search the docs repo for "扩展" in driver docs, and "插件".

Also fetch "framework/core/host/include/hdf_driver_loader.h" to see driver loader interface (kernel vs full).

Let's also check "adapter/khdf/liteos/hdf_driver.mk".

Confirmed: docs contain no ".drv". So the task's item 4 "Driver extension model (.drv file)" needs careful handling. Maybe the ".drv" is from the HDF "driver extension" in LiteOS-M: "驱动的扩展能力：支持驱动编译成.drv文件"? Let me do one more targeted search on Bing/Baidu-like with different phrasing, e.g. "HDF drv 后缀 驱动包" "hdf driver .drv LiteOS". Also search Gitee code via grep_app? grep_app searches GitHub; OpenHarmony mirror on GitHub (openharmony/drivers_hdf_core). Search for ".drv" in repo code maybe.

Actually, I recall from OpenHarmony 1.0/2.0 LiteOS-M: HDF drivers are built into the kernel, and "hdf_driver" template in build/lite produces a "*.drv" file? Hmm, in OpenHarmony's build/lite there is a template `hdf_driver` maybe `output_extension = ".drv"`? Let me check build_lite repo.

Let's clone build_lite sparse and grep for "drv".

Confirmed no .drv. The prompt's ".drv file" premise is likely a confusion with the "drv/" folder in sample repos or with `.drv` in some vendor. I will address it explicitly as a correction with evidence (no .drv in docs/repo, actual forms .so/.z.so/static section/.ko). That is valuable — a claim with counter-analysis.

But wait, maybe ".drv" is the OpenHarmony "driver extension" of "hdf_dev_eco_tool" which generates "driver project" and "driver package"? The DevEco "驱动开发工具" may produce a `.drv` file? Hmm. Let's check hdf_dev_eco_tool README. It's in core/framework/tools/hdf_dev_eco_tool.

Also "hdf-gen" tool. Let's inspect quickly.

Then continue with remaining protocol: at least 8 distinct websearches. So far I've done 5 (hcs hdi-gen, .drv, HDF_INIT, HDI IDL, LiteOS .drv). Need at least 3 more varied:
6. "OpenHarmony HDF platform driver GPIO I2C 适配 SoC 移植"
7. "OpenHarmony Linux kernel HDF khdf patch device tree coexistence"
8. "OpenHarmony driver porting HiSilicon Hi3516 HDF 移植"
9. maybe "OpenHarmony HDF HCS hdf.hcs device_info 启动流程"

Also need to fetch full pages (we fetched raw docs). Need at least one authoritative page about HDF vs Linux driver comparison.

Let's inspect hdf_dev_eco_tool and hdf-gen quickly, then run searches.

Great: official porting doc porting-smallchip-driver-plat.md. Let's fetch it (docs repo now includes zh-cn/device-dev/porting? we only sparse-checked driver + readme). Add porting path sparse.

Also fetch porting-dayu200-on_standard-demo.md (already got highlights). And maybe porting-smallchip-driver-overview.md.

Let me sparse-add porting and read porting-smallchip-driver-plat.md fully.

Then inspect HDF "hdf_device_node.c" launch and "hdf_device_info.h" for preload/policy, plus "DeviceResourceGetIfaceInstance".

Then Linux coexistence: check "patch_hdf.sh" and kernel integration. Read patch_hdf.sh.

Then HDI: fetch drivers_interface README_ZH full (we only got search snippet; fetch raw via gitcode? gitee raw README_zh failed earlier; maybe filename README_ZH.md). Let's fetch https://gitee.com/openharmony/drivers_interface/raw/master/README_ZH.md.

Also hdi-gen usage: "out/gen/xxx/foo_interface_driver.cpp" and hdi.gni. Enough.

Let me batch: sparse porting, README_ZH, patch_hdf.sh.

Read rest of README_ZH for "实现驱动入口" and hcs example.

Also fetch porting-smallchip-driver-overview? Let's check list for "porting-smallchip-driver-*.md": plat, oom. Maybe "porting-smallchip-driver-overview.md" absent. The doc index Readme-CN will show.

Let's read README_ZH rest and porting doc tail (hcs config).

Then Linux kernel coexistence: read patch_hdf.sh, and check "adapter/khdf/linux/patch_hdf.sh".

Also check kernel "drivers/hdf" symlink approach documented in porting-linux-kernel.md (likely describes adding HDF to Linux kernel build). Let's grep.

Batch.

Excellent. porting-linux-kernel.md is exactly about Linux coexistence: HDF is a "OH kernel feature" patched into Linux kernel; the patch symlinks hdf_core into kernel/drivers/hdf. Read section 142-210 fully.

Also "porting-smallchip-driver-oom.md" maybe about OOM? Let's see the doc index for driver porting.

Now, relationship to device tree: HDF uses HCS, not DT. But on Linux, HDF adapters wrap native subsystems; native Linux drivers continue to use DT. Does HDF parse DT at all? Search repo for "of_" / "device_node" / "of_property_read". Let's grep adapter/khdf/linux for of_property.

Also check "hi35xx" pwm driver is a native Linux driver (uses DT probe), not HDF platform. That shows coexistence: HDF platform layer only wraps some subsystems; SoC vendor may also add native Linux drivers.

Let's grep for "of_property_read" and "platform_driver_register" in core repo.

Confirms: HDF does not parse device tree; HCS is the config source. Linux adapters use Linux APIs/subsystems; a vendor may register native Linux platform drivers (hi35xx PWM).

Need to confirm how Linux GPIO adapter enumerates gpiochips (uses gpio_chip list?). Not crucial.

Now HDF architecture components details:
- Driver Config Manager (.hcs) — "HdfAttributeManager", "DeviceResourceIf", hc-gen.
- Device Manager (devmgr_service.c)
- Host/DeviceNode (devhost_service.c, hdf_device_node.c)
- Service manager (devsvc_manager.c)
- PnPManager: hdf_pnp_manager? Search.
- Power manager.

Let's inspect hdf_device_node.c launch to describe Bind/Init/service publish/device node creation (/dev/hdf/xxx), and devsvc_manager.

Also "HdfDeviceObject" property from hcs.

Also hcs parser location: framework/utils? Let's find "hcs_parser".

Batch.

Let me read hdf_device_node.c lines 40-140 to get exact order and note the device node creation.

Also hdf_attribute.c / hcs parser to describe "HdfAttributeManagerGetHostList" reading "hdf_manager" match attr. Let's read hdf_attribute.c.

Also device resource interface "device_resource_if.h" (framework/include/config?) Let's find.

Great. Now I have solid source-level evidence for architecture and boot flow.

Need more on:
- Service manager (devsvc_manager.c) — service publish/get, and user-mode device node creation (/dev/hdf/xxx) via OsalRegisterCdev in driver code. In sample log we saw "/dev/hdf/sample_service".
- Driver message mechanism: HdfIoServiceBind, Dispatch, HdfDeviceSendEvent, event listener. Already documented.
- HDF "device power management" maybe mention.
- OSAL.

Also "Driver Config Manager" — is that a distinct module? In HDF docs, "配置管理" via hc-gen + HCS parser. There's "HdfConfigManager"? Search "DeviceResourceIface" and "HdfConfigSource". We have enough.

Now HDI details: HDI = interface layer, generated proxy/stub, two modes (IPC vs passthrough). Need a primary source for "IPC mode / 直通模式". The SegmentFault article (2022, by OpenHarmony developer) says that. Better: official docs on "HDI" maybe in docs zh-cn/device-dev/driver? Not in driver folder. Could be "zh-cn/device-dev/architecture" or "subsystems". Let's grep docs for "直通模式" across docs (need sparse add more dirs?). We only have driver + porting + readme. Let's grep driver/porting.

Also search web for official HDI overview "HDI 直通模式 IPC 模式 OpenHarmony 官方".

Also need HDF vs traditional Linux driver comparison, design goals (multi-kernel, one-time development). We have overview doc quotes. Good.

Need SoC vendor porting "what to provide":
- device/soc/<vendor>/<soc>/drivers (platform drivers for LiteOS) — porting doc.
- For standard Linux: kernel drivers + HDF patch + hdf_config.
- drivers/peripheral: device drivers (LCD, touch, sensor, audio, camera, WLAN) — repo structure.
- drivers/interface: HDI IDL.
- vendor/<vendor>/<product>/hdf_config/khdf + uhdf.
- vendor kernel config defconfig.

Let's fetch drivers_peripheral README for structure and its role.

Also check "device/soc/hisilicon/common/platform" in patch_hdf cp_list — HiSilicon platform code (wifi). Fine.

Let's fetch drivers_peripheral README_zh.

Now search for official HDI overview doc (maybe "zh-cn/device-dev/driver/driver-peripherals-*-des.md" mentions HDI layers). The drivers_interface README is enough for HDI definition/flow.

Need "HDI two modes" primary source. Search docs for "直通" only in driver folder? grep found none. Could add "zh-cn/device-dev/guide" etc. Maybe architecture docs: "zh-cn/design/..."? Let's do a web search for official doc "HDI 直通模式" and fetch.

Also need "HDI vs HDF relationship" — the task asks. We can explain: HDI is a set of standardized interfaces (IDL) exposed by drivers to system services; implemented by HDI services which are user-mode HDF drivers (uhdf2). Good.

Next: platform driver layer specifics. We have support/platform src dirs including adc, can, clock, dac, dma, gpio, hdmi, i2c, i2s, i3c, mipi, pcie, pin, pwm, regulator, rtc, spi, timer, uart, watchdog. The task listed DAC, TIMER, DMA, MISC — need evidence for those. Let's list include dirs and check "dac", "timer", "dma". Also "misc" is model/misc, not platform.

Check framework/support/platform/include/dac, timer, dma. And adapter/platform (LiteOS-M) only has gpio/i2c/pwm/spi/uart/watchdog/can/mipi_dsi — because for LiteOS-M vendors implement in device/soc dirs.

Let's verify include file names and core structures (GpioCntlr, I2cCntlr, etc.), plus "PlatformManager" service.

Also HDF platform "unified service mode" vs "independent service mode" (I2C doc). Good detail.

Then driver message mechanism details (Dispatch, SBUF, event listener) — already.

Then "device manager" boot: late_initcall on Linux; on LiteOS, DeviceManagerStart at init; user-mode hdf_devmgr process. Need evidence for hdf_devmgr process. AGENT.md says so; adapter/uhdf2/manager/device_manager.c exists. Check.

Let's batch: list platform includes; check device_manager.c; check dac/timer/dma presence.

Good. sdio has no include dir; sdio is in mmc model? Actually adapter/khdf/linux/platform/sdio Makefile only. Check support/platform/src for sdio? It wasn't listed: src had ... spi, timer, uart, watchdog. No sdio. SDIO likely under model/storage/mmc. Task listed SDIO — need accurate: In HDF, SDIO is part of MMC/storage model (framework/model/storage). Let's verify: find model/storage -iname "*sdio*".

Also "misc" model, not platform.

Also "DAC" — exists core. "TIMER" — hdf timer? Let's check timer_core.h contents and whether a "timer" driver is exposed (HdfTimerCreate).

Also "PINCTRL" — pin_core.h (Pin/PINCTRL).

Let me check sdio and misc paths, plus timer.

Good. Now details on GPIO core: GpioCntlr / GpioMethod, gpio_service, GPIO irqs. We have gpio adapter evidence.

Now, "Host/DeviceNode concept" — documented manage.md + hdf_device_node.c + hdf_device_info.h. Let's read hdf_device_info.h struct fields for precise mapping.

Also driver message: hdf_device_desc.h IDeviceIoService.

Let's read those headers key structs.

Great. Now more web searches needed (at least 8 total distinct). So far queries:
1. HDF hcs hdi-gen 详解
2. .drv 文件 动态加载
3. HDF_INIT .hdf.driver section
4. HDI IDL hdi-gen 用户态
5. LiteOS .drv 驱动包
6. 平台驱动移植 SoC hdf_config
That's 6. Need 2+ more. Planned:
7. "OpenHarmony HDF Linux 内核 原生驱动 共存 device tree hcs 对比"
8. "OpenHarmony HDF 与传统 Linux 驱动 区别 优势 多内核"
9. "OpenHarmony hdf_devmgr libhdf_host 进程 驱动加载 服务发布"
10. "OpenHarmony HDF platform driver adapter SoC vendor HiSilicon"

Also maybe fetch full pages for key claims: the 51cto article, aliyun article (we got highlights). "fetch full pages" requirement — we can webfetch a couple of key pages (docs gitee raw already full).

Let's run 3 searches in parallel.

Excellent: HDC2021 article confirms the design goal and "Linux原生驱动和HDF驱动并存" strategy. FOSDEM 2026 slides confirm HDF doesn't replace Linux kernel/DT, wraps DRM/KMS.

Now I need at least 2 more searches to hit 8+ (we're at 8 already: 1 hcs hdi, 2 .drv, 3 HDF_INIT, 4 HDI IDL, 5 LiteOS .drv, 6 platform porting, 7 HDF vs Linux, 8 hdf_devmgr). Good — 8 distinct.

But the task asks "fetch full pages" — I've fetched raw docs and READMEs fully; web snippets are highlights. Let's fetch 1-2 key full pages (HDC2021 article, aliyun article) to satisfy. Also fetch gitee issue full (already partial). Let's webfetch HDC2021 article and the 51cto HDF loading article.

Also need to verify "hdf_config/khdf vs uhdf" in standard system. We have vendor samples.

Additional important items:
- "Driver Config Manager (.hcs/.dts hierarchical configuration)" — note HDF does not use .dts; HCS is its own DSL; on Linux HDF config comes from HCS compiled into kernel image (hdf.hcs -> hcb -> linked as hex). We have Makefile HCS_DIR and hdf_driver.mk hc-gen -b -i. Also "dts" mention: HDF supports "hcs" only; device tree is native Linux. Let's confirm HDF does not parse DTS — grep for "dts" in core repo. Probably nothing. That supports the correction.

- "Device Manager" module: devmgr_service.
- "Host/DeviceNode": yes.
- "Driver extension model": clarify as dynamic loading (dlopen .z.so with driverDesc symbol; kernel static section). Also there's "VDI" (Vendor Device Interface) in HDF: hdf_load_vdi.c loads vendor device interface .so with hdfVdiDesc — this is a form of driver extension! VDI = "vendor device interface"? The doc "driver-peripherals-display-vdi-des.md" exists. That's a newer extension model. Let's check that doc + hdf_load_vdi usage. This may be the closest thing to "driver extension model".

Search for "VDI" in docs and hdf_load_vdi.h.

Also "hdf_dev_eco_tool" is DevEco driver generation tool, not runtime.

Let's investigate VDI and "hdfVdiDesc".

VDI is a display-specific vendor interface, not the general .drv model. hdf_load_vdi.h didn't print (maybe empty path). Let's find it.

Anyway, VDI = Vendor Device Interface: HDF loads vendor .so and dlsym "hdfVdiDesc" — an extension mechanism for vendor display drivers. Good to mention as a real "vendor extension model" distinct from .drv.

Let's find hdf_load_vdi.h path and read the struct.

Also fetch the HDC2021 article full page to quote design goals (multi-kernel, 100K-G).

Let's batch.

The full page fetch failed (bot block). We have highlights with quotes; acceptable but protocol wants "fetch full pages". We fetched raw primary docs fully (overview, manage, porting, READMEs) — that satisfies. For web articles, snippets are enough as secondary corroboration.

Now let's verify a few remaining facts with source:

1. "HDF does not use .dts" — check repo for "dts" references.
2. HCS hierarchical config: "hdf.hcs" includes device_info + per-module configs, compiled by hc-gen into hcb, linked as hex (`hc-gen -b -i`). We have hdf_driver.mk. Also Linux Makefile HCS_DIR. Good.
3. HDI hdi-gen: generated proxy/stub, "libfoo_client_v1.0.z.so"/"libfoo_stub_v1.0.z.so"; HDI service is user-mode HDF driver moduleName "libfoo_driver.z.so" in uhdf device_info.hcs. Good.
4. Platform driver list: verify GPIO/PIN/I2C/SPI/UART/SDIO/PWM/ADC/DAC/REGULATOR/CLOCK/TIMER/WATCHDOG/DMA. We have include dirs; SDIO under model/storage + adapter/platform/sdio; MISC under model/misc.
5. Adapter implementers in vendor dirs: porting doc `device/vendor_name/soc_name/drivers/gpio`; adapter/platform MCU vendors (asr, bes, gr5xx, stm32f4xx, wm); Linux adapters in adapter/khdf/linux/platform; SoC-specific hi35xx pwm/mipi.
6. Boot flow: DeviceManagerInit late_initcall (Linux), DevmgrServiceStartService → GetHostList → StartDeviceHost → install driver → HdfDeviceLaunchNode (Bind→Init→Publish→Attach). Evidence.
7. .drv: no evidence; correct it.

Need one more: "driver message mechanism" details. manage.md covers policy and message APIs. Also HdfDeviceSendEvent, HdfDeviceRegisterEventListener. Good.

Need "Device Manager" description and "service management" — devsvc_manager.

Need "hdf_devmgr user-mode process creates /dev/hdf/dev_mgr" — 51cto article. Good.

Also "HDF 驱动开发模型 vs traditional Linux drivers": 
- HDF: HdfDriverEntry (Bind/Init/Release), HCS config, service publish (policy), message via SBUF, cross-kernel via OSAL/platform APIs.
- Linux: module_init/probe, device tree, file_operations, kernel subsystems.
- Coexistence: HDF wraps Linux native subsystems; HDF is middleware, doesn't replace DT; on standard systems kernel HDF (KHDF) is patched into Linux, user-mode HDF (UHDF) processes publish HDI.

Now "design goals": multi-kernel, 100K-G deployment, one-time development multi-system deployment, elastic framework, standardized interfaces, componentized model, unified config. Quotes from overview.

Now "porting perspective: what SoC vendor must provide":
1. Kernel: device/soc/<vendor>/<soc> (LiteOS platform drivers), device/board/<board> (board code); for Linux: kernel + defconfig.
2. HDF platform adapters: adapter/khdf/linux/platform/* (if using Linux native APIs) or device/soc/.../drivers/* for LiteOS. ModuleName in HCS.
3. HCS: vendor/<product>/hdf_config/khdf/{hdf.hcs, device_info/device_info.hcs, platform/*.hcs} and uhdf/{hdf.hcs, device_info.hcs}.
4. Peripheral drivers: drivers/peripheral/<module>/chipset + drivers/interface/<module>/v1_0 IDL + HDI service (libxxx_driver.z.so) in uhdf HCS.
5. Build integration: Kconfig + Makefile in adapter/khdf/linux/model or platform; defconfig CONFIG_DRIVERS_HDF*; BUILD.gn for user mode.
6. Kernel patch: patch_hdf.sh symlinks hdf_core into kernel/drivers/hdf, applies hdf.patch.

Evidence for #4: drivers_peripheral README + drivers_interface README + a sensor porting article (chipset dir). The official sensor doc path says drivers/peripheral/sensor/chipset.

Let's check docs sensor doc for "chipset" and "drivers/peripheral" paths, and "device/soc" porting doc. Also check porting-dayu200 for "device/board/hihope/rk3568" and hdf_config. We have.

Let me grep docs for "chipset" to confirm vendor driver location.

Also check docs "porting-smallchip-driver-oom.md" maybe irrelevant.

Then compile final answer in Chinese with citations + access date 2026-11-02.

Need permalinks. For gitee, use commit SHA from clone (c5b2c04a...). Gitee blob URLs work: https://gitee.com/openharmony/drivers_hdf_core/blob/<sha>/path#Lx-Ly. Docs repo sha? get git rev-parse in docs clone. vendor_hihope sha? get. Let's collect SHAs.

Also line numbers for key files. Let's compute line numbers for quotes:
- overview.md lines for design goals? Use raw docs at master, but permalink with commit SHA of docs repo.
- manage.md lines for Host/Device/DeviceNode, policy enum, preload, device_info.hcs.
- devmgr_service.c lines.
- hdf_device_node.c lines.
- adapter/khdf/linux/manager/src/devmgr_load.c line 39.
- patch_hdf.sh lines.
- pwm_hi35xx_linux.c line 201.
- gpio_adapter.c line 53.
- i2c_adapter.c line 74.
- uart_adapter.c line 545.

Let's get exact line numbers via grep -n and SHAs.

Now line numbers for source files. Let me gather precise ones.

- devmgr_service.c: DevmgrServiceStartService line? DevmgrServiceStartDeviceHost line 314; StartDeviceHosts 344.
- hdf_device_node.c: HdfDeviceLaunchNode line 90, DeviceDriverBind 65, PublishService 44.
- hdf_driver_loader.c: HdfDriverEntryConstruct line 19, section begin/end.
- driver_loader_full.c: dlopen line 44, dlsym driverDesc line 52.
- patch_hdf.sh: ln_list lines 26-31.
- pwm_hi35xx_linux.c line 201.
- gpio_adapter.c line 53.
- i2c_adapter.c line 74.
- uart_adapter.c line 545.
- hdf_load_vdi.c line 44 dlopen; header HDF_VDI_INIT line.
- hdf_driver.mk hc-gen -b -i line? grep.
- makefile HCS_DIR line.
- hdf_attribute.c GetHdfManagerNode line 34, HdfAttributeManagerGetHostList 58.
- support/platform dirs.

Let me grep line numbers.

Now check whether HDF references "dts" anywhere.

Confirmed: no dts/device tree in HDF core. "设备树" in camera doc refers to logical device tree, not DT.

Let's get HDF_DRIVER_INIT definition lines (maybe in hdf_device_desc.h above 252).

Let me look at platform_manager.h for module types (PLATFORM_MODULE_GPIO etc.), to cite the unified platform manager.

Also check platform device model: "PlatformDevice" + "PlatformManager" abstraction where each subsystem registers.

Then compile answer.

One more thing: "hdf-gen" tool maybe generates driver skeletons; hdf_dev_eco_tool used by DevEco. Task mentions "hdi-gen toolchain" — covered.

"Driver Config Manager" as a named component: HDF docs mention "配置管理" not a "Driver Config Manager" module. In OpenHarmony architecture, there's "hdf_config" module? The AGENT.md says framework/utils HCS parser. There is "config" dir in adapter/khdf/linux? Not present in this repo? Let's check adapter/khdf/linux has no config dir but README earlier (old) mentioned config. Fine.

Let's check "framework/utils/src/hcs_parser" + "interfaces/inner_api/utils/device_resource_if.h" for config access API. Read device_resource_if.h briefly for GetUint32/GetString/GetNodeByMatchAttr.

Also "hdf.hcs" entry naming: vendor sample. Good.

Now also "HDF vs Linux drivers" details: Linux adapter uses native APIs:
- gpio_adapter.c gpio_set_value_cansleep
- i2c_adapter.c i2c_transfer
- uart_adapter.c driver_name ttyAMA
- adc_iio_adapter.c kernel_read IIO sysfs
- pwm_hi35xx native pwm_chip/DT
These are concrete.

Also "sdio" adapter is only in model/storage. Check adapter/khdf/linux/model/storage/sdio_adapter.c uses Linux mmc? quick grep.

Let's do final evidence gathering: platform_manager module list, device_resource_if API, sdio adapter.

Excellent. Now check PlatformManager module enum maybe in platform_module.h? Not needed.

Let's also verify the "hdf_dev_eco_tool" is "driver ecosystem tool" that generates driver templates/HCS — the task item 4 "driver extension model (.drv file)" can be addressed with:
- HDF extension = dynamic driver module (.so/.z.so) + `driverDesc` symbol, or static `.hdf.driver` section; no `.drv`.
- Vendor extension for display = VDI (`hdfVdiDesc`, HdfLoadVdi dlopen).
- hdf_dev_eco_tool is a dev-time generator, not `.drv`.

Let me check hdf_dev_eco_tool capabilities quickly (command_line dirs) to describe it accurately: hdf_add_handler, driver_add, hdi_operate, hdf_defconfig_patch, hdf_linux_scann, etc. This is the "driver ecosystem tool" used to add drivers to build/config. Good.

Also check "hdf_dbg" tool (debug), "hcs-view".

Now, I should ensure the answer covers "Driver Config Manager (.hcs/.dts hierarchical configuration)". I'll explain HCS hierarchy: hdf.hcs (entry) → device_info/device_info.hcs (host/device/deviceNode) + per-module config HCS matched by match_attr; hc-gen compiles to HCB / C macros; no DTS. On Linux, native DT remains for native drivers only.

Need source for "HCS is not DT" — negative evidence (no dts in repo). Also FOSDEM slide says "It does not replace the Linux Kernel or Device Tree". Great citation.

Let's fetch FOSDEM PDF? It's a slide PDF; webfetch may not parse. We have snippet. Could cite URL.

Now platform driver list: need evidence for MISC (model/misc: dsoftbus, light, vibrator) and SDIO (model/storage). Also PIN (pin_core.h) = pinctrl. ADC/DAC/CLOCK/TIMER/DMA/REGULATOR in support/platform.

Let me verify "pin_core.h" contents mention pinctrl functions.

Also "hdmi", "i3c", "mipi", "pcie", "i2s", "can" extras.

Now SoC porting example HiSilicon:
- vendor_hisilicon/hispark_taurus_linux/hdf_config/hdf.hcs includes device/* configs; module "hisilicon,hi35xx_chip".
- device_info moduleName "HDF_PLATFORM_UART", matchAttr "hisilicon_hi35xx_uart_0".
- adapter/khdf/linux/platform/pwm/pwm_hi35xx_linux.c and mipi_tx_hi35xx.c.
- adapter/khdf/linux/platform/Kconfig PWM_HI35XX.
- device/soc/hisilicon/common/platform/wifi copied by patch_hdf.sh.

That's strong.

Need "hdf_config/khdf vs uhdf" for standard system: rk3568 has both; uhdf device_info.hcs lists HDI services (audio_hdi_service etc.) with moduleName libxxx.z.so. We saw uart etc. Let's read a snippet of uhdf device_info.hcs to cite HDI service moduleName `libxxx.z.so`.

Good. Now let's verify "hdi-gen" usage command in hdi.gni or codegen options (--gen-c/--gen-cpp, --intf-type hdi, -d out). We saw build PR diff. Could cite drivers_interface README for generation instead.

Need "HDI two modes" official-ish. Search once more for "HDI 直通模式 IPC模式 OpenHarmony 官方 文档". Also "HDI 接口 部署形态" maybe in "zh-cn/device-dev/driver/driver-peripherals-*-des.md" no. Maybe docs "zh-cn/device-dev/architecture"? Let's websearch.

Also maybe "HDI" overview in "docs/en/device-dev/driver/driver-hdi-overview.md"? Let's list docs repo en/device-dev/driver? We only sparse zh. Try curl a few candidate paths in en. Or search the docs readme for "HDI".

Let's grep docs repo file names for hdi: `ls zh-cn/device-dev/driver | grep -i hdi` → only display-vdi.

Search web quickly.

Also I want a citation for "HDI = Hardware Device Interface" definition and "DAL" layer. The SegmentFault article by OpenHarmony developer is fine, plus drivers_interface README.

Let's do 9th and 10th searches for HDI modes and HiSilicon porting maybe.

We now have plenty. Note one secondary source (Harmony Wiki) has an error: "deviceMatchAttr 用于内核设备树匹配" — false. Good to flag as a counter-claim in CLAIMS: HDF does not use DT; deviceMatchAttr matches HCS match_attr, verified by hdf_attribute.c.

Let me verify that precise code: HdfAttributeManagerGetDeviceList matches deviceMatchAttr to node with match_attr? Let's read hdf_attribute.c rest.

Confirmed.

Now I should check "hdf_device_desc.h" HDF_DRIVER_INIT definition (section). It's in "hdf_device_desc.h" maybe from "hdf_driver.h"? Search.

Great: user-mode hdf_device_section.h defines `struct HdfDriverEntry *driverDesc = &(module);` — exactly the symbol dlsym looks for. This is the "driver extension model": user-mode driver exports `driverDesc`.

Let's read that file (interfaces/inner_api/host/uhdf/hdf_device_section.h) to cite lines.

Perfect: two HDF_INIT implementations — kernel (section) vs user (driverDesc symbol). This is the "driver extension/plugin" model.

Now I have enough to write a comprehensive Chinese report.

But before writing, let me double-check a few numbers/facts:
1. HDF platform list includes "PIN" not "PINCTRL"; PIN = pin controller (pin_core.h with SetPinFunc/SetPinPull/SetPinStrength) — that's pinctrl equivalent.
2. SDIO is under model/storage + adapter/platform/sdio; platform include has sdio_if.h in framework/include/platform/sdio_if.h. Let's confirm `framework/include/platform/sdio_if.h` is the user API. And "adapter/khdf/linux/platform/sdio/Makefile" only — the actual implementation in model/storage/sdio_adapter.c. Fine.
3. MISC = model/misc (dsoftbus/light/vibrator), not a platform bus.
4. Lack of "SDIO" in support/platform/src means it's a storage model thing.
5. "DAC" exists but no Linux adapter? adapter/khdf/linux/platform has adc but no dac. DAC likely only on LiteOS-M via vendor. Check adapter/platform (no dac). So DAC core exists, but Linux adapter absent. Mention accurately: core layer exists; vendor/SoC adapter must implement DacMethod.

6. TIMER: framework/support/platform has timer core (TimerCntrl) — used by drivers, not exposed as HDI.

7. DMA: dmac_core.h.

8. "CLOCK": clock_core.h.

9. "REGULATOR": regulator_core.h + regulator_tree_mgr.h (regulator tree).

10. "WATCHDOG": watchdog_core.h.

Now verify "adapter/platform" MCU vendor list and module names (gpio_bes.c etc.). Could cite directory listing as evidence.

Now, the "hdf_config" for small system path in porting doc: `//vendor/vendor_name/product_name/config/device_info/device_info.hcs`; standard uses `vendor/<product>/hdf_config/khdf`; Linux Makefile confirms `hdf_config/khdf` or `hdf_config` fallback.

Now "kernel patch" evidence: patch_hdf.sh symlinks and applies hdf.patch; porting-linux-kernel; kernel_linux_patches README with common_patch/hdf.patch and per-SoC patch. Good.

Now, "HDI implementations as HDF user-mode drivers": drivers_interface README + uhdf device_info moduleName lib*.z.so. Good.

Now "hdi-gen" is in framework/tools/hdi-gen; but note it's being replaced by idl_tool (ability_idl_tool) per build PR. Mention current state: hdi-gen under framework/tools; build template hdi.gni calls idl tool path (in newer builds) with --intf-type hdi. Be careful; state both, cite code dir + README.

Let me check if framework/tools/hdi-gen is still built/exists in master (yes). And idl-gen dir exists. Fine.

Now produce final answer with:
- 0. 结论摘要 (key corrections: no .drv; HDF doesn't replace DT)
- 1. 设计目标
- 2. 架构组件 (with diagram in text)
- 3. 平台驱动层
- 4. 驱动扩展/加载机制 + boot flow
- 5. 与 Linux 原生驱动/设备树关系
- 6. SoC 移植清单 (HiSilicon concrete)
- 7. 目录速查表
- 8. 常见误解/风险
- ## EXPAND
- ## CLAIMS

Citations: use gitee permalinks with commit SHA and line numbers, plus docs URLs (docs commit b847798...). Access date 2026-11-02.

Let me get exact line ranges for key quotes:
- docs/zh-cn/device-dev/driver/driver-overview-foundation.md lines 5-11 (multi-kernel problem), 29 (HDF def), 67 (platform list), 83-89 (repo table).
- manage.md lines 25 (Host/DeviceNode), 35 (preload), 64-75 (policy), 650+ (device_info.hcs).
- porting-smallchip-driver-plat.md lines 3-30 (dir structure), 40+ (GPIO example), and hcs config near end.
- porting-linux-kernel.md lines 142-160.

Let me get precise line numbers for porting doc hcs section and dir structure.

Now check docs lines 5-11 for design rationale quote (multi-kernel migration).

Now, let's make sure about "at least 8 distinct websearch queries" — I did 10. Good.

"fetch full pages" — fetched raw docs pages: overview, manage, README, porting, drivers_interface README_ZH, drivers_peripheral README, vendor hcs files (full), source files (full). Good.

Now verify a subtle point: Is `adapter/platform` built for LiteOS-M only? Its BUILD.gn. Let's check quickly. And `adapter/khdf/liteos_m` exists. Also `adapter/khdf/liteos` for LiteOS-A. So:
- LiteOS-M: adapter/khdf/liteos_m + adapter/platform (MCU adapters) + device/soc vendor drivers
- LiteOS-A: adapter/khdf/liteos + device/soc vendor drivers
- Linux: adapter/khdf/linux + adapter/uhdf2 (user mode)
- UniProton: adapter/khdf/uniproton

Check adapter/khdf/uniproton exists (yes).

Now "HDF 驱动模型" (Device/Host/DeviceNode) — done.

"Driver Config Manager" — HCS + hc-gen; "HdfAttributeManager" is config manager for hosts/devices; "DeviceResourceIface" for driver private config. Good naming.

"Driver service management" — DevSvcManager + observer.

"PnPManager" — only USB PNP notify; mention USB PnP manager optional.

"Power management" — HdfPowerManager, power_state_token.

Now final answer structure (Chinese, detailed but organized). Need citations everywhere with access date. Use markdown links.

Important: Cite commit-pinned permalinks. Gitee blob URL with SHA. Let me verify one URL works (gitee blocks bots?). Test curl -I on a blob URL.

Also cite docs raw at master plus commit? Use gitee blob with docs SHA b84779874332bd7c2afee0ca3875494fa4793f1f. Test.

Let me test 2 URLs.

Gitee returns 405 to curl HEAD/GET (anti-bot). The links still work in browser. For citations, I can use `https://gitee.com/openharmony/.../blob/<sha>/path#Lx` — acceptable. Alternatively use GitHub mirror (openharmony/docs, openharmony/drivers_hdf_core) with commit SHAs? GitHub mirror SHAs differ (mirror syncs maybe same commits? gitee commits may not match github). Check GitHub repo head SHA via API (needs proxy). Not necessary.

I'll cite gitee paths with SHA, plus raw URLs for verification. The task accepts gitee.

Note: for docs citations, line numbers of working tree at master (sha b847798) are valid.

Now, one more check: hdf "framework/support/platform/src" includes "pcie", "i3c", "i2s", "can", "hdmi" — the task list didn't mention, but I can note extras.

Also "HDF 平台驱动统一服务模式" from I2C doc: one service per type via manager, vs independent. Optional detail.

Now let me verify "hdf.hcs" is the board entry and is compiled by hc-gen into HCB and linked. Evidence:
- Linux Makefile: `obj-$(CONFIG_DRIVERS_HDF) += $(HCS_DIR)/` — compiles vendor hdf_config dir; vendor's Makefile presumably runs hc-gen. Let's check rk3568/hdf_config/khdf/Makefile to see hc-gen command.

Excellent: user-mode HCS compiled to `hdf_default.hcb` + `hdf_devhost.cfg`, installed to /etc. So on standard system, KHDF config is built into kernel image (hdf_hcs_hex.o), UHDF config is a runtime .hcb file in /etc. That's a concrete difference worth stating.

Check uhdf2/hcs/hcs.gni to confirm install path /etc/hdf or similar; and hdf_devhost reads /etc/hdf/hdf_default.hcb? Let's check quickly.

Also HdfGetHcsRootNode / HdfConfigSource. Not necessary.

Let me confirm install path.

Good: user-mode HCB installed to /chipset_base_dir/etc/hdfconfig (or /system/etc/hdfconfig), read at runtime.

Now compile final answer. It should be thorough. Let me plan sections:

**摘要/结论先行** (5 bullets, including correction on .drv and DT)

**1. 设计目标**
- multi-kernel; same hardware different kernels; 100K–100M; one-time development multi-system; elastic; standardized interfaces; componentized; unified config (HCS/HC-Gen).
- Quote from overview.

**2. 架构组成**
Table: 模块 | 代码落点 | 职责
- Driver Framework core: manager/host/shared + DevMgrService, DevHostService, DevSvcManager, DriverInstaller, DriverLoader, DeviceNode, Power.
- Driver Config Manager: hc-gen, HCS parser, DeviceResourceIface, HdfAttributeManager.
- Device Manager: devmgr_service.c; late_initcall / hdf_devmgr process.
- Host/Device/DeviceNode semantics, policy/preload/priority.
- OSAL.
- HDI + hdi-gen + hdi service as user-mode HDF driver.
- Model layer (sensor/display/input/audio/...).
Include boot flow sequence with source lines.

**3. 平台驱动层**
- Layering: 接口层 (if/if_u) / 核心层 (core, manager, unified service) / 适配层 (adapter by SoC).
- Table of device types: GPIO, PIN, I2C, SPI, UART, PWM, ADC, DAC, REGULATOR, CLOCK, TIMER, WATCHDOG, DMA, SDIO, MMC, HDMI, I3C, MIPI, PCIe, CAN.
- Where adapters live: framework/support/platform (core), adapter/platform (MCU LiteOS-M: asr/bes/gr5xx/stm32f4xx/wm), adapter/khdf/linux/platform (Linux wrappers), device/soc/<vendor>/<soc>/drivers (vendor LiteOS adapters), model/storage for SDIO/MMC.
- Concrete Linux adapter examples: gpio→gpiolib, i2c→i2c_transfer, uart→tty, adc→IIO sysfs, sdio→linux/mmc.
- Unified service mode (one manager service) vs independent.

**4. 驱动扩展模型、消息机制、启动流程**
- Correction: no `.drv` file. Two real mechanisms:
  a) kernel: HDF_INIT → .hdf.driver section, driver loader iterates _hdf_drivers_start/end.
  b) user: HDF_INIT → `driverDesc` symbol; host dlopen(moduleName) + dlsym("driverDesc").
  c) VDI (vendor device interface) for display: dlopen vendor .so + hdfVdiDesc.
- Boot flow steps with evidence: late_initcall → DeviceManagerStart → HdfIoServicePublish /dev/hdf/dev_mgr → StartService → GetHostList (match_attr hdf_manager) → per host device list → start host process (user) / logical host (kernel) → AddDevice → loader get driver by moduleName → HdfDeviceNode → Bind (policy 1/2) → Init → PublishService → AttachDevice token.
- Message mechanism: IDeviceIoService.Dispatch, HdfIoServiceBind, SBUF, HdfDeviceSendEvent/listener; policy values.
- HCS compile: hc-gen -b -i -a → hcb linked as hex in kernel; user-mode hcb at /etc/hdfconfig.

**5. 与 Linux 原生驱动 / 设备树的关系**
- HDF ≠ replacement; KHDF patched into Linux kernel via patch_hdf.sh; UHDF user processes.
- HDF adapters wrap Linux subsystems; native drivers remain; example pwm_hi35xx native pwm_chip + DT probe coexisting; uart adapter uses ttyS; adc IIO.
- HDF config is HCS, not DTS; deviceMatchAttr matches HCS match_attr, not DT (correct secondary source error).
- When to migrate: HDI-exposed/distributed capabilities → HDF/HDI; local-only block/net/PMIC → keep native.

**6. SoC 移植交付清单 (HiSilicon 为例)**
Table: 交付物 | 路径 | 说明/证据
1. kernel + defconfig + SoC patch (kernel/linux/patches/<ver>/<device>_patch/*.patch)
2. HDF kernel patch (common_patch/hdf.patch) via patch_hdf.sh; symlinks.
3. platform adapters: adapter/khdf/linux/platform/* (reuse) or SoC-specific (pwm_hi35xx, mipi_tx_hi35xx); LiteOS: device/soc/<vendor>/<soc>/drivers/{gpio,i2c,...} + lite.mk/Kconfig.
4. HCS: vendor/<vendor>/<product>/hdf_config/khdf/{hdf.hcs, device_info/device_info.hcs, platform/*.hcs}; uhdf/{hdf.hcs, device_info.hcs, BUILD.gn}.
5. peripheral drivers + HDI: drivers/peripheral/<module>/chipset; drivers/interface/<module>/v1_0/*.idl + BUILD.gn → lib*_client/stub; HDI service .z.so registered in uhdf device_info.hcs.
6. build integration: Kconfig/Makefile, defconfig CONFIG_DRIVERS_HDF*, BUILD.gn hdf_driver/hdi.
7. verification: /dev/hdf/* nodes, logs "launch devnode", hdf_devmgr ready bootevent.
Include HiSilicon concrete names: "hisilicon,hi35xx_chip", moduleName HDF_PLATFORM_UART, match_attr hisilicon_hi35xx_uart_0; PWM_HI35XX Kconfig; mipi_tx_hi35xx.

**7. 目录速查表**

**8. 易错点/风险**
- .drv myth
- DT myth
- policy semantic confusion (0 none, 1 kernel, 2 kernel+user, 3 subscribe, 4 private) — note some secondary sources say 0=kernel/2=user which is wrong; official enum says otherwise. That's a good correction (Harmony Wiki says policy 0=内核, 2=用户态 — wrong). Flag.
- SDIO not in support/platform core; belongs to storage/mmc model.
- DAC/CLOCK/TIMER/DMA have core but Linux adapter may be absent (DAC) — vendor must implement.
- HDF driver must use OSAL + platform APIs to remain portable.

**EXPAND** leads:
- LEAD: VDI vendor extension (`hdfVdiDesc`) — why: newest extension point beyond HdfDriverEntry — angle: "HdfLoadVdi hdfVdiDesc display VDI 接入".
- LEAD: hdf_dev_eco_tool driver generation — why: automates Kconfig/Makefile/defconfig/hcs edits — angle: "hdf_dev_eco_tool hdf_add_handler driver_add".
- LEAD: UniProton adapter — why: HDF now supports RTOS beyond LiteOS — angle: "drivers_hdf_core adapter khdf uniproton".
- LEAD: hdi-gen vs ability_idl_tool migration — why: build template switched to idl_tool — angle: "hdi.gni idl_tool --intf-type hdi".
- LEAD: user-mode driver performance (IPC hops) — why: 3-4 IPC per HDI call — angle: "HDI IPC 调用 性能 开销 binder".

**CLAIMS**:
1. HDF has no .drv artifact — high risk (contradicts prompt) — sources: gitee docs/core — counter: "OpenHarmony .drv 驱动" — primary: hdf_device_section.h + driver_loader_full.c.
2. HDF does not use device tree; HCS only — normal/high — primary: hdf_attribute.c + no dts refs.
3. Kernel drivers are registered via .hdf.driver section, user drivers via driverDesc + dlopen — high confidence.
4. HDF coexists with Linux native drivers; KHDF patched into kernel — normal.
5. policy enum values — high (secondary sources conflict) — primary manage.md.
6. SDIO is storage/mmc not platform core — normal.
7. Platform adapters for LiteOS live in device/soc/<vendor>/<soc>/drivers — normal.
8. HDI service = user-mode HDF driver .z.so — normal.

Need to be careful: CLAIM requires "SOURCES: domains" and "COUNTER: refutation search".

Now line numbers for citations:

docs overview:
- L5 multi-kernel problem
- L7 100K
- L29 HDF definition
- L37-47 components
- L67 platform list
- L83-89 repo table

manage:
- L25 Host/Device/DeviceNode
- L35 preload
- L64-78 policy
- L650-680 device_info.hcs template

porting-smallchip-driver-plat:
- L4, L7-30 dir, L34, L42-64, L159
porting-linux-kernel:
- L36-40 OH kernel, L142-197

core:
- framework/core/host/src/hdf_device_node.c L44-60 publish, L65-88 bind, L90-125 launch
- framework/core/manager/src/devmgr_service.c L314-341, L344-373, L429-440
- framework/core/common/src/hdf_attribute.c L34-36, L58-95, L150-170
- framework/core/host/src/hdf_driver_loader.c L16-40
- framework/core/common/include/host/hdf_device_section.h L14-15
- interfaces/inner_api/host/uhdf/hdf_device_section.h L21
- adapter/uhdf2/host/src/driver_loader_full.c L28, L44-58
- adapter/khdf/linux/manager/src/devmgr_load.c L25-39
- adapter/khdf/linux/platform/gpio/gpio_adapter.c L46-57
- adapter/khdf/linux/platform/i2c/i2c_adapter.c L59-75
- adapter/khdf/linux/platform/uart/uart_adapter.c L521-550
- adapter/khdf/linux/platform/adc/adc_iio_adapter.c L52-75
- adapter/khdf/linux/platform/pwm/pwm_hi35xx_linux.c L112-135, L201
- adapter/khdf/linux/patch_hdf.sh L24-31
- adapter/khdf/linux/Makefile L24-40
- adapter/khdf/liteos/hdf_driver.mk L44-58
- framework/support/platform/include/fwk/platform_manager.h L20-30
- support/platform/include dirs (no line)
- framework/model/storage/src/mmc/sdio_if.c, mmc_sdio.c
- framework/model/misc dirs

vendor:
- rk3568/hdf_config/khdf/hdf.hcs L1-30
- rk3568/hdf_config/khdf/device_info/device_info.hcs L1-50
- rk3568/hdf_config/khdf/platform/rk3568_uart_config.hcs L1-20
- rk3568/hdf_config/uhdf/device_info.hcs L24-40
- rk3568/hdf_config/uhdf/BUILD.gn L18-30
- hispark_taurus_linux/hdf_config/hdf.hcs L1-22
- device_info L1-45

drivers_interface README_ZH lines: generation, HDI as user-mode HDF driver, moduleName libfoo_driver.z.so, hcs example.
drivers_peripheral README lines.

Line numbers for vendor files: get exact via grep maybe. For hdf.hcs, lines 1-25. For device_info, host platform line 14. UART moduleName line ~60. Let's get exact for hisilicon uart match attr and rk3568 moduleName.

Now let's check the "hdf_config/khdf/hdf.hcs" full content lines (we saw). Good.

One more: "device/soc/.../drivers" doc suggests structure but actual HiSilicon code is in device/hisilicon? Let's check: older OpenHarmony LiteOS-A platform drivers for Hi3516 were in `device/hisilicon/drivers/`. In current repo, `device/soc/hisilicon/hi3516dv300/...`? Let's search web or clone device_soc_hisilicon sparse? There is repo "device_soc_hisilicon". Let's verify to give accurate path.

Quick: git ls-remote / clone sparse device_soc_hisilicon and list.

Also "device/board/hihope/rk3568" for standard. Let's check device_soc_hisilicon tree.

For hi3516dv300 (LiteOS-A), platform HDF drivers may be in device/soc/hisilicon/hi3516dv300/sdk_liteos/...? Let's list hi3516dv300 dirs.

Hi3516dv300 has hdf_config under device/soc/hisilicon/hi3516dv300/sdk_liteos/hdf_config. Where are the platform driver adapters? Maybe in `device/soc/hisilicon/hi3516dv300/sdk_liteos/platform/...`? Let's list sdk_liteos dirs.

Hi3516 LiteOS platform drivers likely live in `device/hisilicon/drivers` (older repo) or in `device/board/hisilicon/hispark_taurus/...`? Hmm. The porting doc says device/vendor_name/soc_name/drivers. For Hi3516, maybe repo "device_hisilicon_drivers" (deprecated). Let's check quickly: gitee.com/openharmony/device_hisilicon_drivers exists? Use ls-remote.

Actually for the report, I can rely on the official porting doc convention (device/<vendor>/<soc>/drivers) and the current repo layout (device_soc_hisilicon/hi3516dv300/sdk_liteos/hdf_config). The platform adapters for Hi3516 may be in `device/board/hisilicon/hispark_taurus/kernel/drivers`? Let's not overreach; say "LiteOS 场景：device/<vendor>/<soc>/drivers（官方移植文档约定）；Hi3516 的 HCS 实际位于 device/soc/hisilicon/hi3516dv300/sdk_liteos/hdf_config" with evidence.

Let's check device_soc_hisilicon hi3516 hdf.hcs to cite.

Notable: "hisi_pl061_driver" (vendor GPIO adapter module name) — evidence SoC vendor supplies adapter with custom moduleName. Great.

Now I have all I need. Let's write the final answer in Chinese, comprehensive but organized. It should be long (exhaustive assignment), with tables and citations.

Citations format: 
[`driver-overview-foundation.md` L5](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-overview-foundation.md#L5)（访问 2026-11-02）

For vendor repo, SHA f7db0a2... and vhis 368808...
For docs SHA b847798...
For core SHA c5b2c04...

Note: gitee blob URLs may 405 for bots but valid for users; mention raw paths too? I'll include repo+path+line, and a note that links are commit-pinned.

Let me be careful about claims:
- "HDF_INIT 在用户态展开为 driverDesc" — verified.
- "kernel 展开为 section .hdf.driver" — verified.
- "driverDesc 符号 dlopen" — verified.
- "hdf_devmgr forks host process per host" — from 51cto answer (secondary) + code DevHostServiceClnt/DevmgrServiceStartHostProcess. We saw `DevmgrServiceStartHostProcess(hostClnt, false, false)`. Let's verify it forks in full adapter (devhost_service_full.c / devmgr_service_full.c). Search "fork".

No fork in uhdf2; probably uses `HdfHostProcessStart` from "hdf_host_process" or launches devhost binary via `posix_spawn`? Search "devhost" in uhdf2 manager.

Important: in user mode, host processes are not forked by devmgr but started via init service control (`ServiceControlWithExtra(hostName, START)`), i.e., each host is an init service defined in `hdf_devhost.cfg` (cfg generated from HCS). That's precise and better than the secondary "fork" claim. Let's check hdf_devhost.cfg content from rk3568 to see host services.

`hdf_cfg("hdf_devhost.cfg")` generates from hdf.hcs via hcs.gni — presumably lists services "hdf_devhost_xxx". Let's read hcs.gni template and generated example? Can't generate, but read template.

`hc_gen_start_cfg` generates init cfg listing host services (each host as a service). So devmgr uses ServiceControl to start host services. Accurate statement: "每个 host 在 init 中注册为独立服务，devmgr 通过 ServiceControlWithExtra 拉起；用户态 host 进程承载驱动 .so" — cite driver_installer_full.c L28-35 + hcs.gni L38-55.

This is better than "fork". Good.

Now, does devhost process dlopen? driver_loader_full.c dlopen(moduleName) where moduleName is "libxxx_driver.z.so"; linker searches lib paths. Good.

Now write the answer. Keep citations compact: use footnotes? Markdown links inline.

I'll write in Chinese, with tables. Include "访问日期 2026-11-02" in citation footnote or a note at top.

Let me draft carefully with accurate line references. I'll use format:
`[docs: driver-overview-foundation.md L29](https://gitee.com/openharmony/docs/blob/b847798.../...#L29)`

For code:
`[hdf_device_node.c L90-125](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04.../framework/core/host/src/hdf_device_node.c#L90-L125)`

For vendor:
`[device_info.hcs L60-67](https://gitee.com/openharmony/vendor_hisilicon/blob/3688080.../hispark_taurus_linux/hdf_config/device_info/device_info.hcs#L60-L67)`

Need ensure vendor_hisilicon SHA and path. Yes.

For rk3568: vendor_hihope SHA f7db0a2, path rk3568/hdf_config/...

For device_soc_hisilicon SHA? clone rev-parse. Let's get.

Now compose. Length: thorough but readable. Use sections 1-8.

Let me make sure every factual claim has a source or is clearly reasoning.

Key quotes (<25 words) in Chinese/English:
- "当相同的硬件部署不同内核时，如何能够让设备驱动程序在不同内核间平滑迁移……" (24 chars? fine)
- "一次开发，多系统部署"
- "HDF驱动架构采用C语言面向对象编程模型构建，通过平台解耦、内核解耦"
- "DeviceHost 仅表示逻辑隔离" (from WeChat article) — good.
- "HDF 不替代 Linux Kernel / Device Tree" (FOSDEM slide) — quote "It does not replace the Linux Kernel or Device Tree".

Now the ".drv" correction: state clearly: In current master (commit c5b2c04, accessed 2026-11-02), `grep -rn "\.drv"` over docs/driver and core finds no `.drv` driver artifact; only `drvCodecName` fields and a sample folder `drv/`. Real artifacts: `.hdf.driver` section (kernel), `driverDesc` (user), `.z.so`, `.ko`/built-in, `.hcb`. So "driver extension model (.drv)" likely a naming confusion; if a vendor uses `.drv` it's project-specific, not HDF spec.

I should be careful not to overclaim "there is no .drv anywhere in OpenHarmony" — say "in the current HDF core repo and official driver docs, no .drv driver format; the framework's own extension points are...". Risk: high, with counter search.

Now "HDF vs traditional Linux drivers" table:
| 维度 | HDF 驱动 | Linux 原生驱动 |
Registration: HdfDriverEntry + HDF_INIT; module_init/probe
Config: HCS (device_info + private), match_attr; DT/ACPI
Service: policy + DevSvcManager/HDI; file_operations/sysfs/class
Messaging: SBUF + Dispatch; read/write/ioctl
Portability: OSAL + platform APIs; kernel APIs
Loading: static section / dlopen .z.so; insmod/built-in
Power: HdfPowerManager listener; runtime PM
Boundary: HDF sits above kernel.

"when coexist": HDF adapters wrap; native drivers stay; only HDI-exposed capabilities need HDF.

"Porting checklist" table with paths and evidence.

Let me also mention HiSilicon specifics:
- hdf.hcs module "hisilicon,hi35xx_chip"
- HDF_PLATFORM_UART + hisilicon_hi35xx_uart_0
- hisi_pl061_driver (GPIO)
- PWM_HI35XX Kconfig + pwm_hi35xx_linux.c (native pwm_chip, DT)
- mipi_tx_hi35xx.c
- device/soc/hisilicon/hi3516dv300/sdk_liteos/hdf_config for LiteOS small system.

Also mention rk3568 as reference for standard system: khdf + uhdf, 1600+ lines (wiki claim) — maybe skip number.

Now EXPAND leads (5).
CLAIMS (7-8).

Let me write.

# OpenHarmony HDF（Hardware Driver Foundation）驱动框架：架构、平台驱动、HDI 与 SoC 移植

> 所有链接均为 **commit 固定（permalink）**；访问日期统一为 **2026-11-02**。
> 主要固定版本：`docs@b847798`、`drivers_hdf_core@c5b2c04`、`vendor_hihope@f7db0a2`、`vendor_hisilicon@3688080`、`device_soc_hisilicon@1ee9126`。

---

## 0. 结论先行（含两处关键纠偏）

1. **HDF 的核心目标不是“再写一套 Linux 驱动”，而是“驱动模型 + 硬件服务接口”的跨内核统一层**：同一套驱动代码通过 OSAL 与平台驱动 API，部署到 LiteOS-M / LiteOS-A / Linux（以及 UniProton）。官方原文：“当相同的硬件部署不同内核时，如何能够让设备驱动程序在不同内核间平滑迁移……是……需要解决的重要问题”，目标是“一次开发，多系统部署”。（[driver-overview-foundation.md L5](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-overview-foundation.md#L5)、[L29](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-overview-foundation.md#L29)）
2. **HDF 不使用设备树（DTS）作为配置源**。HDF 自己的配置语言是 **HCS**，由 `hc-gen` 编译为 HCB（二进制）或 C 宏/源码；`deviceMatchAttr` 匹配的是 HCS 里的 `match_attr`，不是 DT 节点。Linux 原生驱动仍可用 DT，两者互不替代。（源码证据：[hdf_attribute.c L26/L165](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/common/src/hdf_attribute.c#L26)；官方移植文档只讲 HCS，未出现 dts）
3. **“`.drv` 驱动文件”在现行 HDF 中不存在**。HDF 真正的“驱动扩展/插件”机制是两套：
   - **内核态**：`HDF_INIT` 把入口指针放进 ELF section `.hdf.driver`，加载器遍历 `_hdf_drivers_start ~ _hdf_drivers_end`；
   - **用户态**：`HDF_INIT` 展开为导出符号 `driverDesc`，host 进程用 `dlopen(moduleName)` + `dlsym("driverDesc")` 加载 `.z.so`。
   仓库与官方驱动文档中没有任何 `.drv` 驱动格式（详见 §4.1）。
4. HDF 在标准系统上与 Linux 原生驱动**并存**：KHDF 以 patch 方式合入 Linux 内核，平台适配层把 HDF 平台 API 翻译成 Linux 子系统调用（gpiolib、i2c_transfer、tty、IIO、mmc/sdio…）；HDF 不取代 Linux Driver Model。（[patch_hdf.sh L24-31](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/patch_hdf.sh#L24-L31)、[FOSDEM 2026 幻灯片](https://fosdem.org/2026/events/attachments/SYBWKY-bringing_openharmony_to_phones_lessons_from_the_oniro_porting_effort/slides/266916/fosdem_20_qczu0e8.pdf)）
5. SoC 厂商在 HDF 上的交付物可归为 6 类：**内核/补丁、平台适配器、HCS 配置、外设驱动、HDI IDL/服务、构建开关**（§6 给出 HiSilicon 的具体落点）。

---

## 1. 设计目标：为什么需要 HDF

### 1.1 多内核、多容量、一次开发

官方把问题定义得很直接：OpenHarmony 同时支持 Linux 与 LiteOS，同一硬件换内核时，驱动不能重写。HDF 的应对是“平台解耦 + 内核解耦”，用 C 语言面向对象模型构建统一底座。（[L5](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-overview-foundation.md#L5)、[L29-L31](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-overview-foundation.md#L29-L31)）

四项关键能力（同文档 L9-L27）：

| 能力 | 含义 | 工程体现 |
|---|---|---|
| 弹性化框架 | 百 K 级到百兆级设备可裁剪 | 对象管理器按需创建 Manager/Host/Loader；`preload`/`priority` 控制加载 |
| 规范化接口 | 驱动接口稳定、向上兼容 | HDI（IDL 定义）+ 平台驱动统一 API |
| 组件化驱动模型 | 驱动可分层、积木式组合 | `framework/model/{sensor,display,input,audio,...}` |
| 归一化配置界面 | 屏蔽硬件差异、配置与代码解绑 | HCS + HC-Gen；DevEco 配置界面 |

补充自 HDC2021 官方演讲：设计目标还包括“统一硬件 IO 抽象，屏蔽 SoC 芯片差异，兼容 Linux/LiteOS 等内核”，并明确标准系统采取“**内核态 Linux 驱动与 HDF 驱动并存**”的策略。（[HDC2021 驱动框架解读](https://www.e-com-net.com/article/1711894720571060224.htm)）

### 1.2 与传统 Linux 驱动的开发模型差异

| 维度 | HDF 驱动 | 传统 Linux 驱动 |
|---|---|---|
| 注册入口 | `struct HdfDriverEntry { moduleVersion, moduleName, Bind, Init, Release }` + `HDF_INIT()`（[hdf_device_desc.h L202-L252](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/interfaces/inner_api/host/shared/hdf_device_desc.h#L202-L252)） | `module_init()` / `platform_driver.probe` |
| 配置 | HCS：`device_info.hcs`（加载信息）+ 私有配置（`match_attr`） | Device Tree / ACPI / 板级 `platform_data` |
| 对外能力 | `policy` 决定服务发布；`IDeviceIoService.Dispatch` + SBUF 消息 | `file_operations`、sysfs、ioctl、子系统框架 |
| 跨内核 | OSAL + `framework/support/platform` 统一 API | 直接依赖内核内部 API |
| 加载 | 内核：`.hdf.driver` section；用户态：`dlopen` `.z.so` | built-in / `.ko` |
| 生命周期 | `Bind → Init → PublishService → AttachDevice`；失败回滚 `Release` | probe/remove、runtime PM |

HDF 驱动开发被刻意约束为“只使用 HDF 框架接口 + 平台驱动接口”，否则失去跨 OS 特性（官方移植文档原话：“请尽可能只使用HDF驱动框架提供的接口，否则会导致驱动丧失跨OS使用的特性”，[腾讯云转载官方文档](https://cloud.tencent.com/developer/article/1944493)）。

---

## 2. 架构组件：谁负责什么

官方架构图对应五大块：**HDI 层、HDF 驱动框架、统一配置界面、OSAL、平台驱动 + 外设驱动模型**（[L37-L49](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-overview-foundation.md#L37-L49)）。

```
应用 / 系统服务
   │  HDI（IDL 生成的 proxy/stub；IPC 或直通）
   ▼
┌──────────────────────── HDF ────────────────────────┐
│ DevMgrService（设备生命周期）                        │
│   └─ DevHostService（每个 host 一个）                │
│        └─ HdfDevice → HdfDeviceNode → DriverEntry    │
│ DevSvcManager（服务发布/查询） + ServiceObserver      │
│ DriverInstaller / DriverLoader（静态段 or dlopen）    │
│ PowerManager / PnP（USB 可选）                        │
├──────────────────────────────────────────────────────┤
│ framework/model：sensor/display/input/audio/...      │
│ framework/support/platform：GPIO/I2C/SPI/UART/...   │
│ OSAL：mem/lock/thread/semaphore/time/...             │
├──────────────────────────────────────────────────────┤
│ adapter/khdf/{linux,liteos,liteos_m,uniproton}       │
│ adapter/uhdf2（标准系统用户态）                       │
└──────────────────────────────────────────────────────┘
```

### 2.1 Driver Framework 核心（framework/core）

目录按 Manager–Host–Shared 三层组织：

| 子模块 | 代码 | 职责 |
|---|---|---|
| manager | `framework/core/manager/src/devmgr_service.c`、`devsvc_manager.c`、`hdf_driver_installer.c` | 解析 host 列表、启动 host、安装驱动、服务管理 |
| host | `framework/core/host/src/devhost_service.c`、`hdf_device.c`、`hdf_device_node.c`、`hdf_driver_loader.c` | 驱动加载、Bind/Init、服务发布、设备节点 |
| shared | `framework/core/shared/` | Manager↔Host 接口契约、跨进程 token |
| common | `framework/core/common/src/hdf_attribute.c` | 从 HCS 读取 host/device 属性 |

关键源码事实：

- `DevmgrServiceStartService()` 先 `DevmgrServiceStartDeviceHosts()`，再 `DevSvcManagerStartService()`（[devmgr_service.c L429-L440](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/manager/src/devmgr_service.c#L429-L440)）。
- 每个 host：`HdfAttributeManagerGetDeviceList()` 取设备列表；若只有动态设备则不启动 host 进程（[L314-L341](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/manager/src/devmgr_service.c#L314-L341)）。
- 设备启动顺序固定为 **Bind → Init → PublishService → AttachDevice**（[hdf_device_node.c L90-L125](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/host/src/hdf_device_node.c#L90-L125)）。只有 `policy` 为 `PUBLIC(1)` 或 `CAPACITY(2)` 才调用 `Bind`（[L65-L88](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/host/src/hdf_device_node.c#L65-L88)）。

### 2.2 Host / Device / DeviceNode 概念

官方定义非常精确：

> “HDF框架将一类设备驱动放在同一个Host（设备容器）里面……Device对应一个真实的物理设备。DeviceNode是设备的一个部件，Device至少有一个DeviceNode。每个DeviceNode可以发布一个设备服务。每个DeviceNode唯一对应一个驱动。”
> （[driver-hdf-manage.md L25](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-hdf-manage.md#L25)）

层级关系：`host → device → deviceNode`。HCS 模板字段与运行时结构一一对应（`HdfDeviceInfo` 的 `policy/priority/preload/permission/moduleName/svcName/deviceMatchAttr`，[hdf_device_info.h L28-L42](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/interfaces/inner_api/host/shared/hdf_device_info.h#L28-L42)）。

Host 的划分原则：**有依赖的驱动放同一 Host，否则独立 Host**（L25）。用户态部署时 Host 是独立进程；内核态部署时 Host 只是逻辑隔离（官方演讲原文：“当驱动在部署在内核态时，Device Host 仅表示逻辑隔离”，[HDF 驱动框架介绍](https://mp.weixin.qq.com/s/2WhbovdUv8v6x8lmpL4nRg)）。

### 2.3 Driver Config Manager：HCS / HC-Gen / HCS Parser

HCS 是 HDF 的配置 DSL，key-value + node 树，支持 `root/include/delete/template/match_attr`、节点复制、引用修改、数组、bool（[driver-hdf-manage.md L120-L420](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-hdf-manage.md#L120)）。

编译链：

```
.hcs ──hc-gen──> .hcb（二进制）──链接进内核镜像──> HCS Parser 重建配置树
             └─> .c / .h（宏或源码，弱性能环境直接编译）
```

- 内核态标准系统：`hdf_config/khdf/Makefile` 用 `hc-gen -b -i -a` 生成 `hdf_hcs_hex.c`，再编译成 `hdf_hcs_hex.o` 链入内核（[rk3568 hdf_config/khdf/Makefile L42-L58](https://gitee.com/openharmony/vendor_hihope/blob/f7db0a20c513c58d90e5ed0973387dcab65f5787/rk3568/hdf_config/khdf/Makefile#L42-L58)）。
- 用户态标准系统：`hdf_hcb("hdf_default.hcb")` 生成 HCB 并安装到 `etc/hdfconfig`；`hdf_cfg("hdf_devhost.cfg")` 生成 init 启动配置（[uhdf/BUILD.gn L17-L30](https://gitee.com/openharmony/vendor_hihope/blob/f7db0a20c513c58d90e5ed0973387dcab65f5787/rk3568/hdf_config/uhdf/BUILD.gn#L17-L30)、[hcs.gni L17-L55](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/hcs/hcs.gni#L17-L55)）。运行时默认路径 `"/system/etc/hdfconfig"`（[hcb_config_entry.c L29](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/shared/src/hcb_config_entry.c#L29)）。
- 驱动私有配置通过 `DeviceResourceIface` 读取：`GetUint32/GetString/GetNodeByMatchAttr`（[device_resource_if.h L226-L412](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/interfaces/inner_api/utils/device_resource_if.h#L226-L412)）。

`HdfAttributeManager` 的匹配逻辑是纯 HCS：先按 `match_attr = "hdf_manager"` 找 `device_info` 根，再遍历 host/device/deviceNode，把 `deviceMatchAttr` 原样存入 `HdfDeviceInfo`（[hdf_attribute.c L34-L36、L58-L95、L150-L170](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/common/src/hdf_attribute.c#L34-L170)）。**这里没有 DT 解析**。

### 2.4 Device Manager 与用户态多进程模型

- Linux 内核态：`late_initcall(DeviceManagerInit) → DeviceManagerStart()`（[devmgr_load.c L25-L39](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/manager/src/devmgr_load.c#L25-L39)）。
- 标准系统用户态：存在独立守护进程 `hdf_devmgr`，入口 `adapter/uhdf2/manager/device_manager.c`，启动后设置 bootevent `bootevent.hdf_devmgr.ready`（[device_manager.c L28-L55](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/manager/device_manager.c#L28-L55)）。
- 每个 host 不是 devmgr `fork` 出来的，而是注册为 **init 服务**，devmgr 通过 `ServiceControlWithExtra(devHostName, START)` 拉起（[driver_installer_full.c L28-L35](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/manager/src/driver_installer_full.c#L28-L35)）。host 服务名来自 HCS 生成的 `hdf_devhost.cfg`。
- host 进程内用 `dlopen(moduleName)` 加载驱动 `.z.so`，`dlsym("driverDesc")` 取入口（[driver_loader_full.c L28-L58](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/host/src/driver_loader_full.c#L28-L58)）。

### 2.5 HDI 与 hdi-gen：HDF 的“对外接口层”

- HDI 是 **Hardware Device Interface**，位于基础系统服务层与 DAL 之间，用 IDL 描述，编译生成 C/C++ 的 proxy/stub（[drivers_interface README_ZH L1-L15](https://gitee.com/openharmony/drivers_interface/blob/master/README_ZH.md#L1-L15)）。
- 编译模板 `//build/config/components/hdi/hdi.gni`，一个 `hdi("foo")` 目标生成 `libfoo_client_v1.0.z.so` 与 `libfoo_stub_v1.0.z.so`；`module_name` 控制生成的 `HdfDriverEntry.moduleName`（README_ZH L60-L80）。
- HDI 服务本身就是**用户态 HDF 驱动**：实现生成的 `foo_interface_service.h`，编译为 `libfoo_driver.z.so`，再在 `hdf_config/uhdf/device_info.hcs` 里以 `moduleName = "libfoo_driver.z.so"` 注册（README_ZH L110-L150）。
- 两种调用形态：**IPC 模式**（binder，proxy/stub，标准系统默认）与**直通模式**（dlopen 实现库、同进程函数调用，小型系统默认）。（[OpenHarmony 3.1 HDI 介绍](https://segmentfault.com/a/1190000041949372)）
- `hdi-gen` 源码位于 `framework/tools/hdi-gen`（parser/lexer/codegen：C/C++/Java 的 client proxy、service stub、service driver、impl emitter），新构建里逐步由 `ability_idl_tool` 以 `--intf-type hdi` 接管（[hdi-gen 目录](https://gitee.com/openharmony/drivers_hdf_core/tree/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/tools/hdi-gen)、[build PR #3890](https://gitcode.com/openharmony/build/pull/3890/diffs)）。

### 2.6 其余组件

- **OSAL**：mem/lock/thread/semaphore/time/workqueue/cdev/firmware，按内核分实现：`adapter/khdf/linux/osal`、`adapter/khdf/liteos/osal`、`adapter/khdf/liteos_m/osal`（[AGENT.md](https://gitcode.com/openharmony/drivers_hdf_core/blob/master/AGENT.md)）。
- **驱动模型层**：`framework/model/{sensor,display,input,audio,usb,storage,network,misc}`；`misc` 含 dsoftbus/light/vibrator（[目录](https://gitee.com/openharmony/drivers_hdf_core/tree/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/model/misc)）。
- **电源管理**：`hdf_power_manager.c`、`power_state_token.c`；驱动可注册 `IPowerEventListener`（[hdf_device_node.c L128-L145](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/host/src/hdf_device_node.c#L128-L145)）。
- **PnP**：仅 USB PnP notify 作为可选模型（`usb_pnp_manager`），不是全局热插拔框架。

---

## 3. 平台驱动层：统一 API + SoC 适配器

### 3.1 三层结构

官方 I2C 文档把平台驱动讲得最清楚：

| 层 | 职责 | 代码 |
|---|---|---|
| 接口层 | 打开设备、传输、关闭 | `xxx_if.c`（内核 ioctl）/ `xxx_if_u.c`（用户态 IPC/SBUF） |
| 核心层 | 服务绑定、控制器 add/del/get、统一服务发布 | `framework/support/platform/src/<bus>/` |
| 适配层 | 与硬件相关的具体操作（寄存器、时钟、中断） | SoC/单板厂商实现，挂到 `XxxMethod` 钩子 |

原文：“接口层……核心层……适配层：由驱动适配者实现与硬件相关的具体功能”，且 `I2cMethod.transfer` 必须实现，`I2cLockMethod` 可选（[driver-platform-i2c-develop.md L15-L60](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-platform-i2c-develop.md#L15-L60)）。

统一服务模式：同类型控制器很多时，不每个控制器发布一个服务，而由核心层发布**一个 manager 服务**统一管理（I2C 文档 L7-L13）。GPIO/I2C/ADC 在 HCS 里都能看到 `*_MANAGER` + 适配器节点的成对配置。

平台管理器抽象：`PlatformManager` 持有 `PlatformDevice` 链表，按 module 类型获取（[platform_manager.h L20-L58](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/support/platform/include/fwk/platform_manager.h#L20-L58)）。

### 3.2 设备类型与真实代码落点

| 类型 | 核心头文件 | Linux 适配器 | 备注 |
|---|---|---|---|
| GPIO | `gpio/gpio_core.h` | `adapter/khdf/linux/platform/gpio/gpio_adapter.c` | 包 `gpio_set_value_cansleep` / `gpiod_get_direction` |
| PIN（pinctrl） | `pin/pin_core.h` | 无独立 Linux 适配器 | `SetPinPull/GetPinPull/SetPinStrength/SetPinFunc`，即 pinctrl 语义 |
| I2C | `i2c/i2c_core.h` | `.../i2c/i2c_adapter.c` | `i2c_transfer()` |
| SPI | `spi/spi_core.h` | `.../spi/spi_adapter.c` | Linux spi 子系统 |
| UART | `uart/uart_core.h` | `.../uart/uart_adapter.c` | 读 HCS `driver_name`（默认 `ttyAMA`）+ `num`，走 tty |
| PWM | `pwm/pwm_core.h` | `.../pwm/pwm_adapter.c`、`pwm_hi35xx_linux.c` | Hi35xx 直接用 Linux `pwm_chip` + DT probe |
| ADC | `adc/adc_core.h` | `.../adc/adc_iio_adapter.c` | 读 IIO sysfs 节点 |
| DAC | `dac/dac_core.h` | 无 | 厂商需实现 `DacMethod` |
| REGULATOR | `regulator/regulator_core.h`、`regulator_tree_mgr.h` | `.../regulator/` | 支持 regulator tree |
| CLOCK | `clock/clock_core.h` | `.../clock/` | — |
| TIMER | `timer/timer_core.h` | 无独立适配器 | `TimerCntrl`/`TimerCntrlMethod`，供驱动内部定时 |
| WATCHDOG | `watchdog/watchdog_core.h` | `.../watchdog/` | — |
| DMA | `dma/dmac_core.h` | 无独立适配器 | `DmaCntlr`/`DmacCntlrAdd` |
| SDIO/MMC | `framework/model/storage/include/mmc/mmc_sdio.h` | `adapter/khdf/linux/model/storage/sdio_adapter.c` | **不在 support/platform 核心层**，属 storage/mmc 模型 |
| MISC | `framework/model/misc/{dsoftbus,light,vibrator}` | 对应 model 适配 | 不是总线 |
| 其他 | `can/hdmi/i3c/i2s/mipi/pcie` | 部分有 | 见 `framework/support/platform/include` |

证据：`framework/support/platform/include` 与 `src` 下确实存在 `adc can clock dac dma gpio hdmi i2c i2s i3c mipi pcie pin pwm regulator rtc spi timer uart watchdog`（[include 目录](https://gitee.com/openharmony/drivers_hdf_core/tree/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/support/platform/include)）；SDIO 实现在 `framework/model/storage/src/mmc/{sdio_if.c,mmc_sdio.c}`。

### 3.3 SoC 适配器的四种放法（按系统形态）

1. **Linux 标准系统（复用内核子系统）**：`drivers/hdf_core/adapter/khdf/linux/platform/<bus>/`。这些适配器把 HDF 平台 API 翻译成 Linux 原生 API：
   - GPIO：`gpio_set_value_cansleep(cntlr->start + local, val)`（[gpio_adapter.c L46-L57](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/gpio/gpio_adapter.c#L46-L57)）
   - I2C：`i2c_transfer((struct i2c_adapter *)cntlr->priv, ...)`（[i2c_adapter.c L59-L75](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/i2c/i2c_adapter.c#L59-L75)）
   - UART：`driver_name`（`ttyAMA`/`ttyS`）+ `num`（[uart_adapter.c L521-L550](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/uart/uart_adapter.c#L521-L550)）
   - ADC：`kernel_read()` 读 IIO sysfs（[adc_iio_adapter.c L52-L75](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/adc/adc_iio_adapter.c#L52-L75)）
   - SDIO：`linux/mmc/sdio_func.h` + `mmc_host`（[sdio_adapter.c L22-L49](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/model/storage/sdio_adapter.c#L22-L49)）
2. **LiteOS-A/小型系统**：官方移植文档要求厂商在 `//device/<vendor>/<soc>/drivers/<bus>/` 下实现，以 `GpioCntlrAdd()` 注册模型实例（[porting-smallchip-driver-plat.md L4-L64](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/porting/porting-smallchip-driver-plat.md#L4-L64)）。
3. **LiteOS-M/MCU**：`drivers/hdf_core/adapter/platform/<bus>/` 下已有 ASR、BES、GR5xx、STM32F4xx、WM 等厂商实现（如 `gpio_asr.c`、`i2c_bes.c`、`uart_stm32f4xx.c`），`adapter/platform/BUILD.gn` 只编 `gpio i2c pwm spi uart watchdog mipi_dsi`（[BUILD.gn L10-L20](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/platform/BUILD.gn#L10-L20)）。
4. **SoC 专用“原生 Linux 驱动”**：当 Linux 子系统已足够（PWM/DRM/IIO），厂商可直接写 Linux 驱动，不经过 HDF 平台核心。Hi35xx PWM 就是典型：`pwm_chip` + `pwm_ops` + `module_platform_driver`，由 DT 匹配（[pwm_hi35xx_linux.c L112-L135、L194-L201](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/pwm/pwm_hi35xx_linux.c#L112-L201)）。

---

## 4. 驱动扩展模型、消息机制与启动流程

### 4.1 “`.drv` 文件”纠偏与真实的扩展机制

**事实核查**：在 `drivers_hdf_core@c5b2c04` 全仓与 `docs/zh-cn/device-dev/driver` 全目录检索 `.drv`，只命中 `drvCodecName`/`drvDaiName` 字段和示例目录 `drv/`，**没有任何 `.drv` 驱动产物或加载逻辑**。HDF 的扩展/插件机制是：

**(a) 内核态：ELF section 索引**

```c
#define HDF_SECTION __attribute__((section(".hdf.driver")))
#define HDF_DRIVER_INIT(module) \
    const size_t USED_ATTR module##HdfEntry HDF_SECTION = (size_t)(&(module))
```
（[hdf_device_section.h L14-L15](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/common/include/host/hdf_device_section.h#L14-L15)）

加载器用 `_hdf_drivers_start/_hdf_drivers_end` 计算入口数组，逐个 `HdfRegisterDriverEntry()`（[hdf_driver_loader.c L16-L40](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/host/src/hdf_driver_loader.c#L16-L40)）。驱动最终以 `.o/.a` 链入内核（LiteOS）或 `.ko`/built-in（Linux）。

**(b) 用户态：导出 `driverDesc` + dlopen**

```c
#define HDF_DRIVER_INIT(module) struct HdfDriverEntry *driverDesc = &(module)
```
（[uhdf/hdf_device_section.h L21](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/interfaces/inner_api/host/uhdf/hdf_device_section.h#L21)）

host 进程 `dlopen(moduleName)`、`dlsym(handle, "driverDesc")`，`moduleName` 就是 HCS 里的 `libxxx_driver.z.so`（[driver_loader_full.c L44-L58](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/host/src/driver_loader_full.c#L44-L58)）。

**(c) 厂商扩展接口 VDI（Vendor Device Interface，显示域）**

`HdfLoadVdi()` 从 `HDF_LIBRARY_DIR` `dlopen` 厂商库，`dlsym("hdfVdiDesc")`，结构为 `HdfVdiBase{moduleVersion,moduleName,CreateVdiInstance,DestoryVdiInstance}`；宏 `HDF_VDI_INIT(module)` 导出 `hdfVdiDesc`（[hdf_load_vdi.c L44-L60](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/host/src/hdf_load_vdi.c#L44-L60)、[hdf_load_vdi.h L19-L52](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/interfaces/inner_api/host/uhdf/hdf_load_vdi.h#L19-L52)）。官方 Display VDI 文档明确这是“方便芯片厂商接入 OpenHarmony 显示驱动框架模型”的接口（[driver-peripherals-display-vdi-des.md L3-L20](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-peripherals-display-vdi-des.md#L3-L20)）。

> 结论：若某资料写“HDF 驱动编译为 `.drv`”，应视为项目自定义或概念混淆；HDF 规范内没有该后缀。

### 4.2 驱动消息机制

- 服务发布策略 `policy`（[manage.md L64-L78](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-hdf-manage.md#L64-L78)）：
  `0 NONE`、`1 PUBLIC`（内核态）、`2 CAPACITY`（内核+用户态）、`3 FRIENDLY`（可订阅）、`4 PRIVATE`。
- 用户态取服务：`HdfIoServiceBind(serviceName)`；发消息：`serv->dispatcher->Dispatch(&serv->object, cmdCode, data, reply)`；驱动侧实现 `IDeviceIoService.Dispatch`（[manage.md L100-L130、L724-L800](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-hdf-manage.md#L100-L130)）。
- 事件上报：`HdfDeviceSendEvent()` + 用户态 `HdfDeviceRegisterEventListener()`（同文档 L110-L125）。
- 序列化统一用 **SBUF**（`HdfSBuf`），避免不受控内存访问；SBUF 有 `RAW/IPC/IPC_HW` 三种形态（[AGENT.md](https://gitcode.com/openharmony/drivers_hdf_core/blob/master/AGENT.md)）。

### 4.3 启动流程（内核态 Linux 为例，源码级）

```
late_initcall(DeviceManagerInit)                       devmgr_load.c:25-39
  └─ DeviceManagerStart()
      ├─ DevmgrServiceGetInstance()
      ├─ HdfIoServicePublish("/dev/hdf/dev_mgr")
      ├─ DevmgrServiceStartService()                   devmgr_service.c:429
      │   ├─ HdfAttributeManagerGetHostList()          hdf_attribute.c:58
      │   │    └─ 按 match_attr="hdf_manager" 找 device_info，遍历 host，按 priority 排序
      │   ├─ for each host: DevmgrServiceStartDeviceHost()   :314
      │   │    ├─ HdfAttributeManagerGetDeviceList(host)
      │   │    ├─ 只含 preload=2 的 host 不启动
      │   │    └─ DevmgrServiceStartHostProcess()      :56
      │   │         ├─ 内核态：直接构造 DevHostService（逻辑 host）
      │   │         └─ 用户态：ServiceControlWithExtra(hostName, START) 拉起 host 进程
      │   └─ DevSvcManagerStartService()
      └─ host: DevHostServiceClntInstallDriver()       :311
           └─ AddDevice(deviceInfo)
                └─ HdfDeviceNodeNewInstance + driver loader 按 moduleName 找驱动
                     └─ HdfDeviceLaunchNode()           hdf_device_node.c:90
                          ├─ DeviceDriverBind()  (policy 1/2 才调用 Bind)
                          ├─ driverEntry->Init()
                          ├─ HdfDeviceNodePublishService()
                          └─ DevmgrServiceClntAttachDevice()
```

配套证据：`preload` 三值与 `priority` 0–200 的语义（[manage.md L35-L56](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-hdf-manage.md#L35-L56)）；`Bind` 的条件调用与失败回滚（hdf_device_node.c L65-L125）。

---

## 5. 与 Linux 原生驱动、设备树的关系

### 5.1 KHDF：把 HDF “长”进 Linux 内核

`patch_hdf.sh` 做三件事（[L24-L60](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/patch_hdf.sh#L24-L60)）：

```bash
ln -sf ... drivers/hdf_core/adapter/khdf/linux  drivers/hdf/khdf
ln -sf ... drivers/hdf_core/framework           drivers/hdf/framework
ln -sf ... drivers/hdf_core/interfaces/inner_api include/hdf
cp third_party/bounds_checking_function、evdev、SoC wifi 平台代码
patch -p1 < <device>_patch/hdf.patch   # 或 common_patch/hdf.patch
```

之后内核 `drivers/hdf/...` 参与编译；`CONFIG_DRIVERS_HDF=y`、`CONFIG_DRIVERS_HDF_PLATFORM=y` 等开关打开（[porting-linux-kernel.md L142-L197](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/porting/porting-linux-kernel.md#L142-L197)）。SoC 自己的 patch 放 `kernel/linux/patches/<ver>/<device>_patch/<device>.patch`（[kernel_linux_patches README](https://github.com/openharmony/kernel_linux_patches)）。

### 5.2 并存的三种形态

| 形态 | 做法 | 例子 |
|---|---|---|
| HDF 平台核心 + Linux 适配器 | HDF 统一 API 下沉到 Linux 子系统 | GPIO→gpiolib、I2C→i2c_transfer、UART→tty、ADC→IIO、SDIO→mmc |
| HDF 驱动模型 + 厂商原生实现 | 模型归一，底层读写仍调 Linux/寄存器 | Display VDI、Audio ADM（RK809 codec 走 I2C/I2S） |
| 纯 Linux 原生驱动，HDF 只做 HDI 封装 | 内核驱动不动，用户态 HDI Server 翻译 | Camera（V4L2）、WLAN（cfg80211）、部分 Sensor（IIO） |

判断准则（工程实践）：**需要被 OpenHarmony 系统服务统一管理、或需要经 DSoftBus 分布式发布的硬件能力，才纳入 HDF/HDI；块设备、PMIC、内部调试设备可保留原生路径**（[技术栈：多内核兼容与硬件能力发布](https://jishuzhan.net/article/2064589238951292930)）。官方 HDC 演讲也明确：“内核态则使用 Linux 驱动与 HDF 驱动并存的策略”。

### 5.3 与设备树的关系（重要）

- HDF 的配置源是 **HCS**，编译为 HCB 后由 HCS Parser 解析；`deviceMatchAttr ↔ match_attr` 是 HCS 内部匹配（[hdf_attribute.c L150-L170](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/common/src/hdf_attribute.c#L150-L170)）。
- HDF 核心仓库中 `grep -rn "\.dts\|of_property_read\|for_each_child_of_node"` **无命中**；`framework/support/platform` 也不解析 DT。
- Linux 原生驱动继续用 DT：Hi35xx PWM 通过 `platform_driver` + `of_platform` 由 DT 匹配（[pwm_hi35xx_linux.c L118-L201](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/pwm/pwm_hi35xx_linux.c#L118-L201)）。
- 外部资料称“HDF 不替代 Linux Kernel 或 Device Tree，只抽象驱动逻辑与服务发布”（[FOSDEM 2026](https://fosdem.org/2026/events/attachments/SYBWKY-bringing_openharmony_to_phones_lessons_from_the_oniro_porting_effort/slides/266916/fosdem_20_qczu0e8.pdf)），与源码一致。

> 反例提醒：某 Wiki 写“`deviceMatchAttr` 用于内核设备树匹配”，这是**错误**的；它只匹配 HCS `match_attr`。官方 manage.md 与 hdf_attribute.c 均可证伪。

---

## 6. SoC 厂商移植交付清单（以 HiSilicon 为例）

### 6.1 六类交付物

| # | 交付物 | 标准系统（Linux）落点 | 小型系统（LiteOS）落点 | 证据 |
|---|---|---|---|---|
| 1 | 内核 + SoC patch + defconfig | `kernel/linux/patches/<ver>/<device>_patch/*.patch`、`kernel/linux/config/<ver>/<device>_<type>_defconfig` | `kernel/liteos_a` 或 `kernel/liteos_m` + `device/soc/<vendor>/<soc>` | [kernel_linux_patches](https://github.com/openharmony/kernel_linux_patches)、[porting-linux-kernel.md L142-L197](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/porting/porting-linux-kernel.md#L142-L197) |
| 2 | HDF 内核补丁 | `common_patch/hdf.patch` + `patch_hdf.sh` | `drivers/hdf_core/adapter/khdf/liteos*` | [patch_hdf.sh](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/patch_hdf.sh#L24-L31) |
| 3 | 平台适配器 | 复用 `adapter/khdf/linux/platform/*`；SoC 专用则新增（如 `pwm_hi35xx_linux.c`、`mipi_tx_hi35xx.c`） | `device/<vendor>/<soc>/drivers/{gpio,i2c,spi,uart,pwm,watchdog,...}` | [porting-smallchip-driver-plat.md L4-L64](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/porting/porting-smallchip-driver-plat.md#L4-L64) |
| 4 | HCS 配置 | `vendor/<product>/hdf_config/khdf/{hdf.hcs, device_info/device_info.hcs, platform/*.hcs}` + `uhdf/{hdf.hcs, device_info.hcs, BUILD.gn}` | `device/soc/<vendor>/<soc>/sdk_liteos/hdf_config/...`（Hi3516 实例） | [rk3568 hdf.hcs](https://gitee.com/openharmony/vendor_hihope/blob/f7db0a20c513c58d90e5ed0973387dcab65f5787/rk3568/hdf_config/khdf/hdf.hcs)、[hi3516 hdf.hcs](https://gitee.com/openharmony/device_soc_hisilicon/blob/1ee91262fff0ed0f49480d3f4f04536dde4e3793/hi3516dv300/sdk_liteos/hdf_config/hdf.hcs) |
| 5 | 外设驱动 + HDI | `drivers/peripheral/<module>/...`（HAL/HDI 实现）+ `drivers/interface/<module>/v1_0/*.idl` | 同左（用户态） | [drivers_peripheral README](https://gitee.com/openharmony/drivers_peripheral/blob/master/README_zh.md)、[drivers_interface README_ZH](https://gitee.com/openharmony/drivers_interface/blob/master/README_ZH.md) |
| 6 | 构建开关 | `adapter/khdf/linux/{Kconfig,Makefile,platform/Kconfig}` + defconfig `CONFIG_DRIVERS_HDF*` | `device/<vendor>/drivers/lite.mk`、`Kconfig`、`BUILD.gn` | [platform/Kconfig L1-L100](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/Kconfig#L1-L100) |

### 6.2 HiSilicon 具体证据链

**HCS 入口与芯片标识**

`hispark_taurus_linux/hdf_config/hdf.hcs` 先 include 各平台配置，最后 `module = "hisilicon,hi35xx_chip"`（[L1-L22](https://gitee.com/openharmony/vendor_hisilicon/blob/368808023757079ff126f01a739e069e74af3530/hispark_taurus_linux/hdf_config/hdf.hcs#L1-L22)）。LiteOS 版在 `device/soc/hisilicon/hi3516dv300/sdk_liteos/hdf_config/hdf.hcs`，同样模块名，并额外 include `pin/pin_config.hcs`、`dmac/dmac_config.hcs`（[L1-L20](https://gitee.com/openharmony/device_soc_hisilicon/blob/1ee91262fff0ed0f49480d3f4f04536dde4e3793/hi3516dv300/sdk_liteos/hdf_config/hdf.hcs#L1-L20)）。

**平台设备节点（moduleName ↔ 驱动入口 ↔ match_attr）**

```hcs
device_uart :: device {
    device0 :: deviceNode {
        policy = 2;
        priority = 40;
        moduleName = "HDF_PLATFORM_UART";
        serviceName = "HDF_PLATFORM_UART_0";
        deviceMatchAttr = "hisilicon_hi35xx_uart_0";
    }
}
```
（[device_info.hcs L60-L67](https://gitee.com/openharmony/vendor_hisilicon/blob/368808023757079ff126f01a739e069e74af3530/hispark_taurus_linux/hdf_config/device_info/device_info.hcs#L60-L67)）

LiteOS 版 GPIO 节点使用厂商自定义适配器名 `hisi_pl061_driver`（[device_info.hcs L28-L35 附近](https://gitee.com/openharmony/device_soc_hisilicon/blob/1ee91262fff0ed0f49480d3f4f04536dde4e3793/hi3516dv300/sdk_liteos/hdf_config/device_info/device_info.hcs)），说明 **SoC 厂商确实提供自己的平台适配器，并以 moduleName 暴露给 HCS**。

**SoC 专用 Linux 驱动**

- PWM：`adapter/khdf/linux/platform/Kconfig` 有 `PWM_HI35XX`（[L97-L101](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/platform/Kconfig#L97-L101)），实现 `pwm_hi35xx_linux.c`（Linux `pwm_chip`）。
- MIPI DSI：`mipi_tx_hi35xx.c` / `mipi_tx_hi35xx.h`。
- Wi-Fi 平台代码：`patch_hdf.sh` 会把 `device/soc/hisilicon/common/platform/wifi` 拷进内核 `drivers/hdf/`（[L33-L36](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/patch_hdf.sh#L33-L36)），这是 HiSilicon 专有平台代码的典型交付方式。

**标准系统参考板（RK3568）的完整分层**

- `khdf/hdf.hcs` include：device_info、platform（adc/pwm/watchdog/uart/sdio/emmc/spi/i2c）、input、wifi、camera、sensor、audio、light、vibrator、lcd，共 20+ 配置文件，末尾 `module = "rockchip,rk3568_chip"`（[hdf.hcs L1-L29](https://gitee.com/openharmony/vendor_hihope/blob/f7db0a20c513c58d90e5ed0973387dcab65f5787/rk3568/hdf_config/khdf/hdf.hcs#L1-L29)）。
- `khdf/device_info.hcs`：`base_host`（HDF_KEVENT）、`platform_host`（GPIO manager + `linux_gpio_adapter`、WATCHDOG、RTC、UART、I2C manager + `linux_i2c_adapter`、ADC…）。
- `uhdf/device_info.hcs`：HDI 服务全部是 `lib*.z.so`（`libusb_driver.z.so`、`libbluetooth_hci_hdi_driver.z.so`…），`policy = 2`（[L24-L140](https://gitee.com/openharmony/vendor_hihope/blob/f7db0a20c513c58d90e5ed0973387dcab65f5787/rk3568/hdf_config/uhdf/device_info.hcs#L24-L140)）。

### 6.3 移植时的最小闭环（按依赖顺序）

1. **内核能起**：SoC patch + defconfig + `CONFIG_DRIVERS_HDF=y`。
2. **HDF 能起**：`patch_hdf.sh` → `hdf_devmgr`/KHDF 初始化成功（日志 `bootevent.hdf_devmgr.ready`）。
3. **平台设备能枚举**：`hdf.hcs` → `device_info.hcs` → 每个 `moduleName` 有对应驱动入口；`deviceMatchAttr` 有对应 `match_attr`。
4. **平台 API 能通**：GPIO/I2C/UART 至少各验证一个；`/dev/hdf/*` 节点出现。
5. **外设/HDI 能通**：`drivers/interface/*.idl` 生成 proxy/stub；HDI service `.z.so` 在 uhdf HCS 注册；上层服务能 `Get()` 到接口。
6. **可回归**：`CONFIG_DRIVERS_HDF_TEST=y` 跑 HDF 测试集（[porting-linux-kernel.md L199](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/porting/porting-linux-kernel.md#L199)）。

---

## 7. 目录速查表

```
drivers/hdf_core/
├── framework/
│   ├── core/{manager,host,shared,common,adapter,sec}   # 框架核心
│   ├── include/{core,osal,platform,utils,...}          # 对外头文件
│   ├── model/{sensor,display,input,audio,usb,storage,network,misc}
│   ├── support/platform/{include,src}                  # 平台驱动核心（统一 API）
│   ├── tools/{hc-gen,hdi-gen,idl-gen,hcs-view,hdf_dbg,hdf_dev_eco_tool}
│   └── sample/{config,platform}
├── adapter/
│   ├── khdf/{linux,liteos,liteos_m,uniproton}
│   │   └── linux/{manager,platform,model,osal,network,utils}
│   ├── uhdf2/{manager,host,ipc,hdi,hcs,platform,osal,security}
│   └── platform/{gpio,i2c,pwm,spi,uart,watchdog,mipi_dsi,can}  # MCU 适配
├── interfaces/inner_api/{host,utils,hdi,osal}
└── test/

drivers/peripheral/<module>/{hal,interfaces,chipset,...}
drivers/interface/<module>/v1_0/*.idl
vendor/<vendor>/<product>/hdf_config/{khdf,uhdf}/
device/soc/<vendor>/<soc>/...（LiteOS 平台驱动与 hdf_config）
device/board/<board>/...
kernel/linux/patches/<ver>/{common_patch,<device>_patch}/
```

（框架目录来自 [driver-overview-foundation.md L83-L89](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-overview-foundation.md#L83-L89) 与仓库实际树；`adapter/khdf` 含 `linux/liteos/liteos_m/uniproton` 四套。）

---

## 8. 易错点与风险

| 易错点 | 事实 | 证据 |
|---|---|---|
| “HDF 驱动是 `.drv` 文件” | 无此格式；内核是 `.hdf.driver` section，用户态是 `driverDesc` + `.z.so` | [hdf_device_section.h](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/common/include/host/hdf_device_section.h#L14-L15)、[driver_loader_full.c](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/host/src/driver_loader_full.c#L44-L58) |
| “HDF 用设备树配置” | 用 HCS；DT 只属于 Linux 原生驱动 | [hdf_attribute.c](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/core/common/src/hdf_attribute.c#L150-L170) |
| “policy 0=内核、2=用户态” | 官方枚举：0 不发布、1 内核、2 内核+用户、3 可订阅、4 私有 | [manage.md L64-L78](https://gitee.com/openharmony/docs/blob/b84779874332bd7c2afee0ca3875494fa4793f1f/zh-cn/device-dev/driver/driver-hdf-manage.md#L64-L78) |
| “SDIO 在 platform 核心层” | SDIO/MMC 在 `framework/model/storage`，Linux 适配在 `adapter/khdf/linux/model/storage` | [sdio_adapter.c](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/khdf/linux/model/storage/sdio_adapter.c#L22-L49) |
| “所有平台驱动 Linux 侧都现成” | DAC 等只有核心层，无 Linux 适配器，需厂商实现 | [include/dac](https://gitee.com/openharmony/drivers_hdf_core/tree/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/framework/support/platform/include/dac) 与 platform 目录对比 |
| “Host 都是 fork 出来的进程” | 用户态 host 是 init 服务，devmgr 通过 ServiceControl 拉起 | [driver_installer_full.c](https://gitee.com/openharmony/drivers_hdf_core/blob/c5b2c04a7303f0e7d203a56dd064be59a25ee4de/adapter/uhdf2/manager/src/driver_installer_full.c#L28-L35) |
| “HDF 会替换 Linux 驱动” | 并存；只在需要 HDI/分布式治理时封装 | HDC2021、FOSDEM 2026 |

---

## EXPAND

- **LEAD: 显示 VDI 是 HDF 官方“厂商扩展接口”的样板** — WHY: 它用 `hdfVdiDesc` + `dlopen` 实现“驱动插件”，比 HdfDriverEntry 更接近任务里说的“驱动扩展模型”，且官方有专门接入文档 — ANGLE: `HdfLoadVdi hdfVdiDesc display VDI 接入 vendor so`
- **LEAD: `hdf_dev_eco_tool` 自动化移植** — WHY: 它能自动改 Kconfig/Makefile/defconfig/device_info.hcs，直接决定 SoC 移植效率 — ANGLE: `hdf_dev_eco_tool hdf_add_handler driver_add hdi_operate 源码`
- **LEAD: UniProton 适配层** — WHY: `adapter/khdf/uniproton` 说明 HDF 已扩到 LiteOS/Linux 之外的 RTOS，是“跨内核”卖点的最新证据 — ANGLE: `drivers_hdf_core adapter khdf uniproton HDF 移植`
- **LEAD: hdi-gen → ability_idl_tool 迁移** — WHY: 新构建用 `idl_tool --intf-type hdi`，旧 `hdi-gen` 可能被弃用，影响移植工具链选择 — ANGLE: `hdi.gni idl_tool --intf-type hdi hdi-gen 废弃`
- **LEAD: UHDF 多进程 IPC 开销** — WHY: 用户态驱动每次 HDI 调用可能多次跨进程，影响性能敏感模块（Camera/Audio） — ANGLE: `OpenHarmony HDI IPC 调用 性能 binder 开销 devhost`

## CLAIMS

- **CLAIM: 现行 HDF 不存在 `.drv` 驱动产物；内核态用 `.hdf.driver` section，用户态用 `driverDesc` 符号 + `dlopen(.z.so)`** — RISK: high — SOURCES: gitee.com/openharmony/drivers_hdf_core, gitee.com/openharmony/docs — COUNTER: `OpenHarmony HDF .drv 驱动文件 后缀` — PRIMARY: `framework/core/common/include/host/hdf_device_section.h#L14-L15` + `adapter/uhdf2/host/src/driver_loader_full.c#L44-L58`
- **CLAIM: HDF 的配置源是 HCS 而非设备树；`deviceMatchAttr` 匹配 HCS `match_attr`** — RISK: high — SOURCES: gitee.com/openharmony/drivers_hdf_core, gitee.com/openharmony/docs — COUNTER: `OpenHarmony HDF device tree dts deviceMatchAttr` — PRIMARY: `framework/core/common/src/hdf_attribute.c#L150-L170`
- **CLAIM: HDF 设备启动顺序为 Bind→Init→PublishService→AttachDevice，且只有 policy 1/2 调用 Bind** — RISK: normal — SOURCES: gitee.com/openharmony/drivers_hdf_core — COUNTER: `HDF HdfDeviceLaunchNode Bind Init 顺序` — PRIMARY: `framework/core/host/src/hdf_device_node.c#L65-L125`
- **CLAIM: 标准系统用户态 host 由 init 服务拉起（ServiceControl），不是 devmgr fork** — RISK: normal — SOURCES: gitee.com/openharmony/drivers_hdf_core — COUNTER: `hdf_devmgr fork host 进程` — PRIMARY: `adapter/uhdf2/manager/src/driver_installer_full.c#L28-L35`
- **CLAIM: HDF 平台驱动在 Linux 上通过适配器包装原生子系统（gpiolib/i2c_transfer/tty/IIO/mmc），并与原生驱动并存** — RISK: normal — SOURCES: gitee.com/openharmony/drivers_hdf_core, fosdem.org — COUNTER: `HDF 替换 Linux 驱动模型` — PRIMARY: `adapter/khdf/linux/platform/{gpio,i2c,uart,adc}/*.c`
- **CLAIM: LiteOS 平台驱动适配由 SoC 厂商在 `device/<vendor>/<soc>/drivers/<bus>` 实现，并注册 `GpioCntlrAdd` 等模型实例** — RISK: normal — SOURCES: gitee.com/openharmony/docs, gitee.com/openharmony/device_soc_hisilicon — COUNTER: `OpenHarmony 平台驱动 移植 device/soc drivers` — PRIMARY: `zh-cn/device-dev/porting/porting-smallchip-driver-plat.md#L4-L64`
- **CLAIM: HDI 服务本质是用户态 HDF 驱动（`libfoo_driver.z.so`），由 IDL 生成 proxy/stub，支持 IPC 与直通两种模式** — RISK: normal — SOURCES: gitee.com/openharmony/drivers_interface, segmentfault.com — COUNTER: `HDI 与 HDF 区别 HDI 实现方式` — PRIMARY: `drivers_interface/README_ZH.md#L110-L150`
- **CLAIM: HiSilicon Hi35xx 的 HDF 交付包含 `hisilicon,hi35xx_chip` HCS、`HDF_PLATFORM_UART` + `hisilicon_hi35xx_uart_0`、`PWM_HI35XX` 与 `pwm_hi35xx_linux.c`、`mipi_tx_hi35xx.c`** — RISK: normal — SOURCES: gitee.com/openharmony/vendor_hisilicon, gitee.com/openharmony/drivers_hdf_core, gitee.com/openharmony/device_soc_hisilicon — COUNTER: `Hi3516 HDF 平台驱动 适配` — PRIMARY: `vendor_hisilicon/.../hdf_config/device_info/device_info.hcs#L60-L67` + `adapter/khdf/linux/platform/{Kconfig,pwm,mipi_dsi}`
