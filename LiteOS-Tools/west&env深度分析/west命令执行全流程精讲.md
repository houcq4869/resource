# west 命令执行全流程精讲——以 `west update` 为例的 13 步逐站拆解

> 撰写日期：2026-10-09 ｜ 代码基线：west v1.4.0（commit `746e1b19`，`~/workspace/repo/west`）
> 定位：本文是《west源码阅读指南》的进阶篇——把"从敲下回车到进程退出"的完整链路拆成 13 步，每步按 **【要解决的问题 → 代码现场 → 逐段走读 → 实验证据 → 设计观察 → 小结 → 自测】** 的固定格式展开。
> 前 10 步（⓿–⑩）是**所有命令共用的高速公路**；第 11 步起才进入 `west update` 自己的领地。
> 所有实验均已在 Ubuntu 22.04 / git 2.34 / west 1.4.0 上实测，输出原样收录。
> 行号引证与系列文档一致。

---

## 总览：13 步流水线

```
west update
 │ ⓿ 入口：pip 胶水脚本 → main() → WestApp()：13 个命令对象就位
 │ ① parse_early_args：手搓迷你解析器，提前拿到命令名 + verbosity
 │ ② west_topdir()：向上找 .west 路标 ──► topdir
 │ ③ Configuration(topdir)：读三级配置（.west/config + ~/.westconfig + /etc/westconfig）
 │ ④ load_manifest()：west.yml →校验→ Project 图（import 递归合并）【失败仅存 self.mle】
 │ ⑤ load_extension_specs()：扫 west-commands.yml，只登记名字（惰性工厂）
 │ ⑥ load_aliases()：读 [alias] 配置
 │ ⑦ setup_parsers()：内置命令真注册 + 扩展命令占坑
 │ ⑧ run_command()：别名展开 → parse_known_args → 查 builtins 字典分发
 │ ⑨ run_builtin()：调 verbosity + 兑现延迟错误（update ∈ 白名单）
 │ ⑩ WestCommand.run()：注入 config/topdir/manifest 三件套 + hooks → do_run
 │ ⑪ update_all()：带 importer 重解析清单（先 update 再读 import）→ 遍历项目
 │ ⑫ 每项目 update()：init→fetch→update-ref manifest-rev→策略判定→submodules
 │ ⑬ 收尾：失败聚合 → CommandError → sys.exit
```

| 阶段    | 步骤  | 产出                          |
| ----- | --- | --------------------------- |
| 就绪    | ⓿–① | 命令对象表、命令名、日志级别              |
| 感知环境  | ②–④ | topdir、config、manifest（三件套） |
| 可扩展层  | ⑤–⑦ | 扩展登记表、别名表、argparse 树        |
| 分发与注入 | ⑧–⑩ | 选定命令 + 三件套注入                |
| 命令领地  | ⑪–⑫ | git 编排执行                    |
| 退场    | ⑬   | 退出码                         |

---

# ⓿ 第 0 步：从敲下回车到 `WestApp` 就位

## 要解决的问题
west 进程的第一个 Python 语句从哪来？应用状态放在哪？

## 代码现场

```toml
# pyproject.toml
[project.scripts]
west = "west.app.main:main"     # pip 据此生成 ~/.local/bin/west
```

pip 生成的胶水脚本（真实文件，9 行）：

```python
#!/usr/bin/python3
import re
import sys
from west.app.main import main
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main())
```

```python
# main.py:1196-1199
def main(argv=None):
    app = WestApp()
    app.run(argv or sys.argv[1:])
```

## 逐段走读

**① 入口链**：`west` → pip 生成的胶水 → `main()` → `WestApp().run(['update'])`。
`re.sub(...)` 是 Windows 上修剪 `west.exe`/`west-script.pyw` 名字用的；`sys.exit(main())` 是**第 13 步的退出码离开进程的地方**。

**② 为什么用类不用全局变量**（main.py:199-201 注释原文）：*我们可以用全局变量，但那样就很难在同一个 Python 进程里白盒测试多次 main() 调用，而这是一个目标（issue #149）。*——面向对象在这里的唯一理由是**可测试性**。

**③ `__init__` 的 13 个 `None` 字段 = 整个程序的状态地图**（main.py:203-216）：

```python
self.topdir = None          # ← 第 2 步填
self.config = None          # ← 第 3 步填
self.manifest = None        # ← 第 4 步填
self.mle = None             # 清单加载失败的异常 ← 第 4 步失败时存，第 9 步引爆
self.builtins = {}          # ← ★本步就填
self.extensions = {}        # ← 第 5 步填
self.aliases = {}           # ← 第 6 步填
self.builtin_groups / self.extension_groups / self.west_parser /
self.subparser_gen / self.cmd / self.queued_io ...
```

**④ 本步唯一的实事：实例化 13 个命令对象**（:218-221）：

```python
for group, classes in BUILTIN_COMMAND_GROUPS.items():
    lst = [cls() for cls in classes]                                  # 全部 new 一遍
    self.builtins.update({command.name: command for command in lst})  # 名字 → 实例
    self.builtin_groups[group] = lst
```

数据源 `BUILTIN_COMMAND_GROUPS`（:1204-1225）：git 管理组 9 个（Init/Update/List/ManifestCommand/Compare/Diff/Status/ForAll/Grep）+ 其他组 3 个（Help/Config/Topdir）+ 隐藏组（SelfUpdate）。

**边界**：`Update()` 被实例化 ≠ 被执行——此刻没解析参数、没碰文件，只是把名字/help/`requires_workspace=True` 等静态属性登记好。**实例化是"备货"，执行是第 10 步之后的事**。

**⑤ help 的后门**（:233）：`self.builtins['help'].app = self`——注释自认 "A dirty layering violation"。因为 argparse 没有从子 parser 爬回主 parser 的正规通道，而 `west help` 两者都要。**读源码样本：理想分层向现实需求妥协时，认账的注释就是设计文档。**

## 自测
1. `pip uninstall west` 后 `west update` 报什么？为什么与 west 源码无关？
2. 把 `Update` 从注册表删掉，`west update` 死在哪一步？（→ 第 8 步 handle_unknown_command）
3. `self.builtins` 为什么用字典不用列表？（→ 第 8 步 `'update' in self.builtins`）

---

# ① 第 1 步：`parse_early_args`——手搓迷你解析器

## 要解决的问题：一条"鸡生蛋"死锁链

```
想建完整的 argparse 树
  → 树上要有扩展命令 → 扩展来自 west.yml → 路径来自 .west/config → 要先找到 .west
    → 但 west -V 根本不需要工作区！
```

解法：**先用 80 行 if-elif 提取"任何情况下都要尽早知道"的信息，其余留给 argparse**。

官方理由（`EarlyArgs` 注释，main.py:70-92）：
1. 命令是扩展但不在工作区时，给出更友好的报错；
2. **verbosity 决定日志级别**——而清单解析（第 4 步）的日志也要受 -v 控制，所以必须更早。

## 代码现场（main.py:137-169 主循环）

```python
for arg in argv:
    if expecting_zephyr_base:      zephyr_base = arg
    elif arg.startswith('-h'):     help = True; consume_more_args(arg[2:])
    elif arg.startswith('-v'):     verbosity += 1; ...
    elif arg.startswith('-q'):     verbosity -= 1; ...
    elif arg.startswith('-z'):     # -z PATH / -z=PATH / -zPATH 三形态
    elif arg.startswith('-'):      unexpected_arguments.append(arg)  # ★只记账不报错
    else:
        command_name = arg         # ★第一个非选项 token = 命令名
        break                      # ★后面的 token 是命令自己的参数，与我无关
```

`consume_more_args`（:106-135）用递归处理 `-hVv` 这类**合并短选项**（-h+-V+-v）。

## 三个关键语义

1. **command_name = 第一个非选项 token，找到即 break**。`['update']` → `'update'`，没有更玄的机制。
2. **unexpected_arguments 只记账**。`west --foo update` 的 `--foo` 留给"懂全部参数"的 argparse 报——手搓解析器只对自己认识的一小撮负责，**克制是它不出错的原因**。
3. **verbosity 是净计数**：`-v` 加 1、`-q` 减 1。`west -v -v -q` = 净 +1。

## 实验证据：全局选项必须在命令名之前

```
$ west -v list        ✅ verbosity=1，正常
$ west list -v        ❌ west list: error: unexpected arguments: ['-v']
```

写法 2 死因：`list` 之后的 token 归子 parser 管，`List` 没注册 `-v` 且 `accepts_unknown_args=False` → 死在第 10 步的闸门（commands.py:173-174）。

## `run()` 的前四个消费动作（main.py:238-250）

```python
early_args = parse_early_args(argv)
logging.getLogger('pykwalify').setLevel(logging.CRITICAL)  # ① 校验库闭嘴，报错文案 west 自己写
self.setup_west_logging(early_args.verbosity)              # ② ★在解析清单之前设定级别！
colorama.init()                                           # ③ Windows ANSI / 非 tty 剥色
```

`setup_west_logging`（:669-683）：`>=2 → DEBUG, 1 → INFO, 0 → WARNING, -1 → ERROR, else CRITICAL`，挂到 `west.manifest` logger。

**伏笔**：`early_args.command_name` 此刻没人消费——它要到第 8/9 步才用（unknown command 报错、坏清单白名单判断）。**现在生产，后面消费**。

## 自测
1. `west -qV` 输出什么？`west -z update` 会发生什么？
2. `unexpected_arguments` 为什么不当场报错？（提示：`west init -o=--depth=1` 的 `-o=...` 该谁认识？）
3. 把 `-v` 挪到 argparse 建树之后处理，损失什么？

---

# ② 第 2 步：`west_topdir()` 与 `.west` 路标

## 要解决的问题：命令在任意子目录执行，怎么知道工作区根在哪？

## `.west` 是什么：一个只装一张藏宝图的路标目录

```
west-lab/                 ← topdir（工作区根）
├── .west/                ← ★ 路标：存在本身 = "根在这里"
│   └── config            ← 藏宝图（3 行）：
│       [manifest]
│       path = manifest   # 清单仓相对路径
│       file = west.yml   # 清单文件名
├── manifest/  lib/  app/ ...
```

设计问答：
- **为什么是目录不是文件**：config 要住在里面；`is_dir()` 顺带排除同名文件误判。
- **为什么配置不放清单仓**：`west.yml` 是"工作区有哪些仓"（公共声明、可 import）；`.west/config` 是"本机的事实与偏好"（私有）。
- **命名陷阱**：`west_topdir` 返回 `.west` 的**父目录**；要 `.west` 本身用 `west_dir()`（util.py:54-63）。

## 代码现场（util.py:65-86，全文 22 行）

```python
def west_topdir(start=None, fall_back=True):
    cur_dir = pathlib.Path(start or os.getcwd())
    while True:
        if (cur_dir / WEST_DIR).is_dir():
            return os.fspath(cur_dir)
        parent_dir = cur_dir.parent
        if cur_dir == parent_dir:                  # Path('/').parent == Path('/') → 到根了
            if fall_back and os.environ.get('ZEPHYR_BASE'):
                return west_topdir(os.environ['ZEPHYR_BASE'],
                                   fall_back=False)   # 换起点再试一次，且只试一次
            raise WestNotFound('Could not find a west workspace '
                               'in this or any parent directory')
        cur_dir = parent_dir
```

细节：①根检测靠 `Path('/').parent == Path('/')`；②**就近优先**——遇到的第一个 `.west` 就返回；③`fall_back=False` 防兜底死循环（设想 `ZEPHYR_BASE=/`）；④`start` 参数让算法可注入起点 = 可测试。

## 实验证据（全部实测）

```
实验1（深层子目录）：cd lib/src/some/deep/dir && west topdir → /tmp/west-lab   # 向上遍历
实验2：cat .west/config → [manifest] path=manifest file=west.yml
实验3（嵌套工作区）：inner-ws 里跑 → /tmp/inner-ws（就近者赢）
实验4a（工作区外）：
  FATAL ERROR: no west workspace found from "/tmp"; "west topdir" requires one.
    - Change directory ... / Set ZEPHYR_BASE ... / Run "west init" ...
实验4b：ZEPHYR_BASE=/tmp/west-lab west topdir（在 /tmp 下）→ /tmp/west-lab
```

**实验 4a 的精妙：两层错误接力**——

```
第 2 步现场：west_topdir() 抛 WestNotFound
  → main.py:255-258 捕获，不当错误！topdir=None，继续走
  → 一路传到第 10 步 WestCommand.run() 的闸门（commands.py:176-177）
  → die(_no_topdir_msg(...))  ← 你看到的 FATAL ERROR 来自这里，不是异常原文
```

**发现在底层，决策在上层**：`west init/help/config` 在工作区外必须能跑，所以"没找到"是不是致命，由每个命令的 `requires_workspace` 自己决定。

## 设计对比

| | git | west |
|---|---|---|
| 向上找标记目录 / 就近优先 | ✅ `.git` | ✅ `.west` |
| 环境变量 | `GIT_DIR` **直接指定**（优先于遍历） | `ZEPHYR_BASE` 只是遍历失败的**备选起点**（语义不同） |
| 跨 mount | 默认不跨（可配） | 无此概念 |

## 自测
1. 在 `lib/` 下建空 `.west`：`west topdir` 返回 lib，但 `west list` 死于找不到 manifest——为什么？（路标有了，藏宝图没了）
2. `ZEPHYR_BASE` 与 `GIT_DIR` 语义差在哪？
3. `west_topdir` 为什么不缓存结果？

---

# ③ 第 3 步：`Configuration`——三级配置的读取与合并

## 要解决的问题：把三级配置文件一次性读进内存，供全进程使用。

## 代码现场

```python
# main.py:260-266
self.config = west.configuration.Configuration(topdir=self.topdir)
self.config._copy_to_configparser(west.configuration.config)   # 遗留兼容，见 3.7

# configuration.py:163-179
def __init__(self, topdir=None):
    local_path = _location(ConfigFile.LOCAL, topdir=topdir, find_local=False) or None
    self._system = _InternalCF.from_path(...)   # 文件不存在 → None（三态！）
    self._global = _InternalCF.from_path(...)
    self._local  = _InternalCF.from_path(...)
```

| 级别 | 默认路径 | 环境变量覆盖 |
|---|---|---|
| SYSTEM | `/etc/westconfig` | `WEST_CONFIG_SYSTEM` |
| GLOBAL | `~/.westconfig`（XDG 时 `$XDG_CONFIG_HOME/west/config`） | `WEST_CONFIG_GLOBAL` |
| LOCAL | `<topdir>/.west/config` | `WEST_CONFIG_LOCAL` |

两个细节：① `from_path` 对不存在的文件返回 **None 而非报错**（三级都是可选的）；② `find_local=False`——找 LOCAL 不自己去文件系统搜索（那是第 2 步的职责），只信 topdir 拼路径。**发现工作区归 util，读文件归 Configuration。**

## 读路径：10 行优先级瀑布（:228-253）

```python
def _get(self, getter, default, configfile):
    for cf in self._whence(configfile):     # [local, global, system]
        if cf is None: continue
        try:    return getter(cf)           # 第一份命中 → 返回
        except KeyError: pass               # 这层没有 → 落到下一层
    return default
```

四个类型化 getter（get/getboolean/getint/getfloat）全部长一个样：`self._get(lambda cf: cf.get(option), ...)`——**getter 是传进来的 lambda**，让 `_get` 不关心类型转换，10 行服务四个 API。

## 写路径：与读不对称

```python
def set(self, option, value, configfile=ConfigFile.LOCAL):   # ★默认 LOCAL
```

- **读默认 ALL，写默认 LOCAL**：读问"生效值是什么"（综合三层），写问"我的偏好记在哪"（默认最私有，不会惊吓式改 `/etc/westconfig`）。
- `set(..., ALL)` **直接拒绝**（全写无语义）；`delete` 却**允许 ALL**（全删有明确语义）——不带作用域时只删最高优先级那份。
- 文件不存在懒创建（`_create` 连父目录一起建）。
- **写入是立即全量重写，无并发锁**——类文档字符串自认（:150-152）。

## 实验证据（实测，GLOBAL 用环境变量隔离到临时文件）

```
$ west config demo.color blue            # 无作用域 → 落在 .west/config（local）
$ WEST_CONFIG_GLOBAL=/tmp/fake.cfg west config --global demo.color red
$ west config demo.color                 # local=blue vs global=red
blue                                     # ★ local 赢（就近优先）
$ west config -d demo.color              # 删的是 local 那份
$ west config demo.color
red                                      # ★ 删一层露一层
```

## 3.7 那行"遗留兼容"是什么

`west.configuration.config` 是模块级**全局** configparser（:419）。往里抄一份是因为 west 1.0 前的扩展用模块级 API（`read_config()` 等）。**双轨制**：老轨道全标 DeprecationWarning，west 2.0 移除——与 `log.py` 同一个故事（issue #149）。

## 设计观察：像 git config 却不调 git config

三级文件、就近优先、`section.key` 全是 git config 的翻版，但**实现零交互**（全库无 `git config` 子进程）：模仿接口语义，不复用实现。另外文档字符串（:154-156）：*"WEST_CONFIG_* 环境变量在且仅在 Configuration 对象创建时生效"*——**构造即快照**，测试可把每个用例指向独立临时文件。

## 下游消费者
第 4 步用 `manifest.path/file` 找 west.yml；第 5 步用 `commands.allow_extensions`；第 11 步用 `update.fetch/narrow/path-cache/name-cache/sync-submodules`。

## 自测
1. `--global` 和 `--local` 各设一次同名键，`west config --list` 里出现几次？值是什么？
2. 为什么 set 禁 ALL 而 delete 允许？
3. 进程建好 Configuration 后，别人在另一终端改了 `~/.westconfig`，这个进程看得到新值吗？

---

# ④ 第 4 步：`load_manifest`——从两行配置到一张项目图（最长的一站）

## 要解决的问题：把 west.yml 这份**意图声明**变成程序可操作的对象图。

## 代码现场（main.py:280-303）

```python
def load_manifest(self):
    if not self.topdir:
        return                                    # 工作区都没有，跳过
    try:
        self.manifest = Manifest.from_topdir(topdir=self.topdir,
                                             config=self.config)
    except (ManifestVersionError, MalformedManifest, MalformedConfig,
            ManifestImportFailed, FileNotFoundError, PermissionError) as e:
        self.mle = e                              # ★ 失败不 die！存起来
```

注释（:292-302）说明了为什么延迟：*也许没问题，比如用户正在跑 `west config manifest.path foo` 来修复 MalformedConfig——但要等解析完命令行才知道。* 六种异常全部延后，**意外异常照常向上冒**（fail fast）。

## 解析流水线（manifest.py）

```
.west/config 说 manifest.path=manifest, file=west.yml
  → Manifest.from_topdir → from_file（:1233-1301）
  → _load：yaml.load(SafeLoader/CSafeLoader :211)
  → validate()（:537-601）：
      ① 顶层必须有 'manifest' 键
      ② version 预检查（对照 SCHEMA_VERSION='1.2' + _VALID_SCHEMA_VERS 白名单）
      ③ pykwalify.core.Core(source_data, manifest-schema.yml).validate()
         → SchemaError 包装成 MalformedManifest（附文件路径 + schema 路径）
  → _load_validated（:1992 起）语义解析：
      ① self: → ManifestProject（名字硬编码 'manifest'，FIXME #327）
      ② defaults/remotes → _defaults NamedTuple + url_bases 字典
      ③ projects 逐条 _load_project（:2337-2459）：
           url 优先级：显式 url > remote+repo-path > defaults.remote
           url = url_bases[remote] + '/' + (repo-path 或 name)
           path = path_prefix / 显式path 或 name（路径逃逸校验 :2429-2457，
                  拒绝绝对路径/../进 .west）
      ④ import 递归合并（见下）
      ⑤ _check_paths_are_unique（:2728）
      ⑥ ManifestProject 硬插 projects[0]
```

schema 有三个"刻意的洞"：`import`/`submodules` 声明为 `any`（运行时细查），`west-commands` 只许 `str`（list 只会在 import 合并时内部产生）。

## import 递归——本步的核心

**机制：递归构造新 Manifest 实例 + 共享同一个可变 `_import_ctx`**（manifest.py:2225-2242 / 2583-2608）：

```python
child_ctx = self._ctx._replace(
    path_prefix=self._ctx.path_prefix / imap_path_prefix,   # 标量字段换新的一层
    current_data=data, manifest_west_commands=[])
Manifest(topdir=self.topdir, internal_import_ctx=child_ctx) # 递归！但 ctx.projects
                                                            # 还是同一个 dict 对象
```

- **先到先得**：`_add_project`（:2690-2704）向共享 dict 写入，重名忽略。
- **解析顺序**（:1992-1999 文档明确）：**self 导入 → 本文件 projects → 项目导入**，先解析者胜。
- **读取来源分两条路**：`self: import:` 走文件系统（目录则按序读全部 *.yml）；项目 `import:` 从 **git 的 manifest-rev** 读（`_manifest_content_at` :252，`git ls-tree`，tree 时读目录全部 *.yml）。
- **无显式环检测**：靠 `RecursionError` 兜底转 `_ManifestImportDepth`（:686，作者自认 hack）。

### 实验证据 A：-vv 看解析实况

```
$ west -vv list
west.manifest: DEBUG: loading /tmp/west-lab/manifest/west.yml
west.manifest: DEBUG: resolving self import extra.yml
west.manifest: DEBUG: found submanifest file: extra.yml
west.manifest: DEBUG: loading /tmp/west-lab/manifest/extra.yml
west.manifest: DEBUG: group-filter: unset
west.manifest: DEBUG: added project dup path dup revision main
west.manifest: DEBUG: added project extra path extra revision main
west.manifest: DEBUG: loaded /tmp/west-lab/manifest/extra.yml
```

### 实验证据 B：import 优先级（反直觉，必做）

west.yml 定义 `dup=lib.git` 且 `self: import: extra.yml`；extra.yml 定义 `dup=app.git` + `extra=app.git`：

```
$ west list -f "{name:8} {url}"
dup      .../remote/app.git    ← 被导入文件（extra.yml）的 dup 赢了！
extra    .../remote/app.git
lib      .../remote/lib.git
```

**本文件的 dup 被覆盖**——因为 self 导入**先解析**。规则是"先解析者胜"，不是"导入者胜"。

## 对 update 的特殊伏笔：鸡生蛋问题

项目 import 的内容从各仓 git 的 `manifest-rev` 读——可有的仓**还没克隆**。此刻（第一次解析）读不到它们，**第 11 步会带着 importer 回调重新解析一遍**。

## REPL 玩法（比读更有效）

```python
>>> from west.manifest import Manifest
>>> m = Manifest.from_file('~/west-lab/manifest/west.yml')
>>> [p.name for p in m.projects]
>>> m.projects[1].url, m.projects[1].path, m.projects[1].revision
```

## 自测
1. 手写 3 项目 west.yml（一个 remote、一个 url、一个靠 defaults），纸上算 url/path 再用 REPL 验证。
2. 为什么 self 导入会赢过本文件？（先解析者胜 + 顺序：self→本文件→项目导入）
3. `west list` 和 `west update` 看到的 projects 一定一样吗？（不——update 带 FORCE_PROJECTS 重解析）

---

# ⑤ 第 5 步：`load_extension_specs`——只登记名字，绝不 import 模块

## 要解决的问题：`west help` 要能列出所有扩展命令，但启动不能因此变慢。

## 代码现场（main.py:388-429 + commands.py:604-692）

```python
# main.py:389-394 —— 三态 extensions
if self.manifest is None:
    self.extensions = None     # None=无法确定（清单挂了）≠ {}=确实没有
    return
path_specs = extension_commands(self.config, manifest=self.manifest)
```

```python
# commands.py:_ext_specs（:633-670）逐文件处理：
escapes_directory 防目录逃逸          # 安全闸
→ 文件不存在就跳过（项目没克隆，不算错）
→ yaml.load(SafeLoader)
→ pykwalify 校验 west-commands-schema.yml
→ _ext_specs_from_desc：每个命令条目 → WestExtCommandSpec(name, project, help, _ExtFactory)
```

然后过滤（main.py:411-429）：**撞内置命令名（影子）丢 + queued_io 排队警告；扩展间重名丢 + 警告**。

## 设计观察

- **惰性工厂是本步灵魂**：扫 YAML 便宜（毫秒），import Python 模块贵（可能几秒）。此刻只造 `_ExtFactory` 这个"承诺"，真正 import 推迟到命令被选中（`run_extension`）。
- **对 `west update` 完全无用**，但每次都要扫——因为 help 需要全名单。`commands.allow_extensions=false` 可整体禁用（安全阀）。
- `west-commands.yml` 的 schema 极简：`west-commands: [{file: str, commands: [{name?, class?, help?}]}]`，name/class 缺省互为默认。
- 三态 `extensions`：None（清单坏）/ {}（无扩展）/ dict（正常）——`west help` 据此打印不同提示。

## 自测
1. 一个项目没克隆，它的扩展命令会出现在 `west help` 里吗？（不会——文件不存在被跳过）
2. 扩展命令与内置命令重名，谁赢？（内置，警告排队）

---

# ⑥ 第 6 步：`load_aliases`——别名表

## 代码现场（main.py:431-437，全文 7 行）

```python
def load_aliases(self):
    if not self.config:
        return
    self.aliases = {
        k[6:]: Alias(k[6:], v) for k, v in self.config.items()
        if k.startswith('alias.')
    }
```

配置里 `[alias]` 节的每个键值对（如 `uu = update --narrow`）变成一个 `Alias`（WestCommand 子类，有自己的 parser）。消费在第 8 步的**展开循环**。

**细节**：`k[6:]` 切掉 `alias.` 前缀；空别名的守门在第 8 步（"empty alias" 报错）。

## 自测：别名能套别名吗？（能——第 8 步的 while 循环；`aliases.pop` 防环）

---

# ⑦ 第 7 步：`setup_parsers`——搭 argparse 树，扩展只占坑

## 代码现场（main.py:457-532）

```python
def setup_parsers(self):
    west_parser, subparser_gen = self.make_parsers()
    real_command_names = set()

    for name, command in self.builtins.items():        # ① 内置：真注册
        real_command_names.add(name)
        command.add_parser(subparser_gen)               #    → do_add_parser 全套参数

    if self.extensions:                                 # ② 扩展：只占名字的坑
        for specs in self.extension_groups.values():
            for spec in specs:
                real_command_names.add(spec.name)
                subparser_gen.add_parser(spec.name, add_help=False)   # ★ stub

    if self.aliases:                                    # ③ 别名：注册，除非影子
        for name, alias in self.aliases.items():
            if name not in real_command_names:
                alias.add_parser(subparser_gen)
```

`make_parsers`（:492-532）：`WestArgumentParser(prog='west', add_help=False, west_app=self, allow_abbrev=False)`；`-h` 用自定义 `WestHelpAction`（帮助要分组排版+含扩展）；`-v/-q` 各自 `action='count'`（**argparse 侧分开计数，第 8 步再相减**——与手搓解析器的净计数对齐）；`-V` 用 version action。

**两份解析器的对齐契约**（:507 注释原话）：*If you update these, also update parse_early_args()*——改全局参数必须两处同步。

`Update` 的 `do_add_parser` 在这一步注册自己的参数：`--rebase`、`--keep-descendants`、`--narrow`、`--group-filter`、`-x/--exclude`、`--fetch-strategy`、`--path-cache/--name-cache`、`--stats` 等。

## 自测：为什么 stub 用 `add_help=False`？（真 parser 要等扩展模块 import 后才有帮助文本；占坑只需要名字）

---

# ⑧ 第 8 步：`run_command`——解析与分发

## 代码现场（main.py:534-584）

```python
# ① 别名展开（循环，因为别名可以套别名）
while early_args.command_name in aliases:
    alias = aliases.pop(early_args.command_name)       # pop = 防无限循环
    for i, arg in enumerate(argv):                     # 在 argv 里找到命令名替换
        if arg == early_args.command_name:
            argv = argv[:i] + alias.args + argv[i+1:]
            break
    early_args = early_args._replace(command_name=alias.args[0])

# ② 友好报错先于 argparse
self.handle_early_arg_errors(early_args)
# ③ 解析（known + unknown 分离）
args, unknown = self.west_parser.parse_known_args(args=argv)
# ④ 遗留日志对齐（净计数契约）
log.set_verbosity(args.verbose - args.quiet)
# ⑤ help 路由
if args.help or args.command is None:
    args.command = 'help'
# ⑥ 分发
if args.command in self.builtins:
    self.run_builtin(args, unknown)
else:
    self.run_extension(args.command, argv)
```

## 两个闸门的分工

**`handle_early_arg_errors`（:643-663）**：命令既非内置也非扩展 → 在 argparse 报晦涩错误**之前**给人话：

```
有 topdir：'workspace X does not define this extension command -- try "west help"'
无 topdir：'do you need to run this inside a workspace?'
```

**`parse_known_args` 而非 `parse_args`**：把 unknown 留给 `accepts_unknown_args=True` 的命令（Diff/Status/Grep）透传给 git；Update 不接受，unknown 将在第 10 步被拒。

**`self.cmd` 在两分支里都会被设置**（:579-580 注释）：为了让下面的异常处理块能用它打印错误。

第 ⑬ 步的异常阶梯就挂在 ⑥ 外面（try/except），本步先记住结构。

## 自测
1. 别名 `a = b`、`b = update`，`west a` 会怎样？（两轮展开到 update）
2. 为什么分发查字典而不是 if-elif 链？

---

# ⑨ 第 9 步：`run_builtin`——开跑前兑现所有伏笔

## 代码现场（main.py:685-698）

```python
def run_builtin(self, args, unknown):
    self.queued_io.append(
        lambda cmd: cmd.dbg('args namespace:', args,
                            level=Verbosity.DBG_EXTREME))     # ① 极详尽时打印参数
    self.cmd = self.builtins.get(args.command, self.builtins['help'])  # ② 选定命令（help 兜底）
    adjust_command_verbosity(self.cmd, args)                   # ③ -v/-q 平移进命令
    if self.mle:
        self.handle_builtin_manifest_load_err(args)            # ④ ★兑现第 4 步的雷
    for io_hook in self.queued_io:                             # ⑤ 排队消息挂成 hook
        self.cmd.add_pre_run_hook(io_hook)
    self.cmd.run(args, unknown, self.topdir,
                 manifest=self.manifest, config=self.config)   # ⑥ 进第 10 步
```

## 延迟错误的完整决策树（:305-386）

```python
no_manifest_ok = ['help', 'config', 'topdir', 'init', 'manifest', 'update']

ManifestVersionError（清单版本太新，west 太老）:
    help     → 警告"拿不到扩展帮助，多数命令跑不了"
    config/topdir → 警告"本命令可跑，但多数不行"
    init     → 放行（init 自己会带上下文报错）
    其他     → die
其他错误：命令不在白名单 → 按异常类型 die：
    MalformedManifest/MalformedConfig → "can't load west manifest: ..."
    _ManifestImportDepth → "import loop"（提示 west -v manifest --resolve 调试）
    ManifestImportFailed → die …… ★除非命令是 update：直接 return（没事！）
    FileNotFoundError   → 提示检查 .west/config 的 manifest.file/path
命令在白名单 → 诊断闭包排队（等 verbosity 确定后由 hook 吐），命令照常跑
```

**update 为什么在白名单**（:311-315 注释）：*update 有时安全有时不安全，但必须列入——因为它是修复"某个被 import 项目的 manifest-rev 指向坏清单"的唯一途径。*

**为什么用闭包排队而不是立刻打印**：此刻 verbosity 还没最终确定（adjust 刚做完，hook 里打印能保证落在正确的输出级别），且消息要在命令自己的上下文里出现。

## 自测
1. 清单坏了，哪 6 个命令还能跑？update 为什么必须在内？
2. `ManifestImportFailed` 且命令是 update，为什么直接 return？

---

# ⑩ 第 10 步：`WestCommand.run()`——三件套注入，命令的成人礼

## 代码现场（commands.py:171-200，全文核心 12 行）

```python
def run(self, args, unknown, topdir, manifest=None, config=None):
    self.config = config                            # ① config 最先（die 要查 color.ui）
    if unknown and not self.accepts_unknown_args:
        self.parser.error(f'unexpected arguments: {unknown}')   # ② 闸门一
    if not topdir and self.requires_workspace:
        self.die(_no_topdir_msg(os.getcwd(), self.name))       # ③ 闸门二
    self.topdir = os.fspath(topdir) if topdir else None
    self.manifest = manifest                        # ④ 三件套齐了
    for hook in self._hooks:
        hook(self)                                  # ⑤ 吐延迟的警告/诊断
    self.do_run(args, unknown)                      # ⑥ 命令真正的逻辑
```

前 9 步的全部产出在此汇合：`topdir`（第2步）、`config`（第3步）、`manifest`（第4步）注入命令实例；两个闸门分别拦截"多余参数"和"没有工作区"。

## 三次实验对应的三道闸

| 实验 | 撞的闸 |
|---|---|
| `west list -v` → error: unexpected arguments: ['-v'] | ②（List 不收 unknown） |
| 工作区外 `west topdir` → FATAL ERROR no west workspace | ③（Topdir requires_workspace=True） |
| 工作区外 `west init` → 正常运行 | ③ 放行（init requires_workspace=False） |

`Verbosity` 阶梯（commands.py:83-111）：`QUIET=0, ERR=1, WRN=2, INF=3(默认), DBG=4, DBG_MORE=5, DBG_EXTREME=6`。`-vv` 时凡是经 WestCommand 子进程助手跑的命令都回显命令行（`_log_subproc`，:302-305）；`-vvv` 时 `die()` 改抛 RuntimeError 逼出完整栈（:511-524）。

**从此往下（⑪⑫）是 `west update` 自己的领地，其他命令各走各的 `do_run`。**

---

# ⑪ 第 11 步：`Update.do_run` → `init_state` → `update_all`

## 代码现场一：do_run（project.py:1130-1140）

```python
def do_run(self, args, _):
    self.die_if_no_git()          # shutil.which('git')，找不到就死
    self.init_state(args)         # 读配置、校验 --group-filter
    if not self.args.projects:
        self.update_all()         # 无项目参数 → 全量
    else:
        self.update_some()        # 指定项目名 → 受限模式
```

## 代码现场二：init_state（:1142-1176）

读四个配置 + 解析 group-filter + 定 fetch 策略：

```python
self.narrow = args.narrow or config.getboolean('update.narrow')
self.path_cache = args.path_cache or config.get('update.path-cache')
self.name_cache = args.name_cache or config.get('update.name-cache')
self.sync_submodules = config.getboolean('update.sync-submodules', default=True)
# --group-filter 每项必须 +/- 开头且是合法组名，否则 die
self.fs = self.fetch_strategy()   # CLI 参数 > update.fetch 配置 > 'smart'
```

`fetch_strategy`（:1311-1322）：配置值非法（不是 always/smart）→ 警告并忽略。

## 代码现场三：update_all（:1178-1207）——本步最关键的动作：**重新解析清单**

```python
self.updated = set()
self.manifest = Manifest.from_file(
    importer=self.update_importer,              # ★回调：遇到 import 项目时
    import_flags=ImportFlag.FORCE_PROJECTS)     #   "先 update 它，再读它的 west.yml"

failed = []
for project in self.manifest.projects:
    if isinstance(project, ManifestProject) or project.name in self.updated:
        continue                                 # 跳过清单仓自己、已处理过的
    try:
        if not self.project_is_active(project):
            self.dbg(f'{project.name}: skipping inactive project')
            continue                             # 跳过 group-filter 禁用的
        self.update(project)                     # → 第 12 步
        self.updated.add(project.name)
    except subprocess.CalledProcessError:
        failed.append(project)                   # ★失败不中断，聚合处理
self._handle_failed(self.args, failed)
```

**为什么重新解析**：第 4 步的"鸡生蛋"在这里解决——第一次解析时，未克隆项目的 import 内容读不到；这次带着 importer 回调，import 链上的每个项目都**先 update 再贡献清单内容**（`ImportFlag.FORCE_PROJECTS` 强制 import 走回调而不读本地 git）。

## 代码现场四：update_importer 回调（:1209-1244）

```python
def update_importer(self, project, path):
    if isinstance(project, ManifestProject):
        if not project.is_cloned():
            self.die("manifest repository {project.abspath} was deleted")  # ← 注意：缺 f 前缀，真 bug！
    else:
        assert not project.groups         # manifest API 保证 groups 与 import 互斥
        self.update(project)              # ★ 先 update 这个被 import 的项目
    self.updated.add(project.name)
    try:
        return _manifest_content_at(project, path, Manifest.encoding)  # 再读它的 west.yml
    except FileNotFoundError:
        self.die(...)   # 附修复提示：改 revision / 去掉 import
```

## update_some 的限制（:1246-1309）

`west update PROJECT` 只允许**清单仓直接定义**的项目。两步走：先用 `ImportFlag.IGNORE_PROJECTS` 解析出清单仓自己的项目；若名字不在其中，再用完整解析检查它是否是 import 来的——是则拒绝：*Only plain "west update" can currently update them.*（理由见 :1250-1255 注释：被 import 项目的更新语义没想清楚——要不要先强制更新导入者？）

## 自测
1. update 为什么要解析清单两次？两次的差异是什么参数？
2. update_all 里三行 continue 各跳过谁？
3. `west update some-imported-proj` 为什么被拒绝？

---

# ⑫ 第 12 步：每项目 `update()`——80 行的 git 序列

## 灵魂前置：manifest-rev 三空间解耦

```
 项目仓的 git ref 空间
 refs/heads/manifest-rev ──► ● 新版本   「清单意图」（west update 唯一有权移动）
 refs/west/*              ──► (临时)    「fetch 中间态」（用完即删）
 HEAD / 你的分支           ──► ● 你的工作（west 绝不强行覆盖）
```

## 八步序列（project.py:1376-1457，对照实验场读）

| # | 动作 | git 命令 | 实验证据 |
|---|---|---|---|
| 1 | ensure_cloned | `git init [--initial-branch=init_placeholder]`（≥2.28 防 git 猜名）+ `git remote add origin <url>` | 首次 update 的 "initializing" |
| 2 | 免 fetch 短路 | smart 策略 + revision 是本地已有 tag/commit → 直接跳第 4 步 | — |
| 3 | fetch | 非SHA：`git fetch -f <url> <revision>`，取 `FETCH_HEAD^{commit}`；SHA 且非 narrow：refspec `refs/heads/*:refs/west/*` **全量暂存分支**（祖先判断要用） | 实验 B "fetching, need revision main" |
| 4 | **移动意图指针** | `git update-ref -m 'west update: moving to ...' refs/heads/manifest-rev <sha>`（:2136） | 实验 B reflog：`manifest-rev@{0}: west update: moving to f963504` |
| 5 | 清理中间态 | 逐个 `git update-ref -d refs/west/*`（:1668-1687） | 实验 A：update 后只剩 manifest-rev 一个 ref |
| 6 | 修悬空 HEAD | HEAD 无效则 `git checkout --detach refs/heads/manifest-rev`（:1689-1715） | — |
| 7 | **策略判定**（:1732-1761） | `git rev-parse --abbrev-ref HEAD` + `is_ancestor_of`；三选一见下 | 实验 D1/D2 |
| 8 | 子模块 | `git submodule sync --recursive` + `update --init [--rebase] --recursive`（:1324-） | — |

第 7 步的三选一（:1413-1440）：

```python
if self.args.keep_descendants and is_ancestor:
    # 后代分支被检出且用户要求保留 → 什么都不做（连 HEAD 都不挪）
elif try_rebase:                                  # --rebase 且当前在分支上
    project.git('rebase ' + QUAL_MANIFEST_REV)
else:
    project.git(['checkout', '--detach', sha])    # 默认：挪 HEAD，绝不碰你的分支
    self.post_checkout_help(...)                  # 并给出精确的 rebase 建议
```

## 实验证据（实测）

**实验 A**（update 后的 ref 空间）：

```
$ cd lib && git show-ref
cc4b2623... refs/heads/manifest-rev     ← 只有这一个！没有 origin/*（west 用显式 refspec fetch）
$ git status -sb
## HEAD (no branch)                     ← detached
```

**实验 B**（远端前进后再 update）：

```
$ git reflog show refs/heads/manifest-rev
f963504 refs/heads/manifest-rev@{0}: west update: moving to f963504...   ← -m 的留言
cc4b262 refs/heads/manifest-rev@{1}: west update: moving to cc4b262...
```

**实验 D1**（默认策略，本地有分支 my-work）：

```
HEAD is now at 0601993 lib v3
WARNING: left behind lib branch "my-work"; to rebase onto the new HEAD:
  git -C lib rebase 0601993e... my-work
# git branch: * (HEAD detached at 0601993) / manifest-rev / my-work ← 分支完好！
```

**实验 D2**（分支领先时 --keep-descendants）：

```
west update: left descendant branch "my-work" checked out; current status:
## my-work    ← 这次 HEAD 没被挪走
```

## 彩蛋：一个真 bug（:1422）

```python
if take_stats:
    start = perf_counter()
project.git('status')
if take_stats:
    stats['get current status'] = perf_counter - start   # ← 少了一对括号！
```

`perf_counter`（函数对象）减 float 必然 TypeError——但只有 `--stats --keep-descendants` 组合才走到这行。**读源码一课：参数检查型 bug 藏在配置组合的角落里。**

## 自测
1. SHA revision 为什么要用 `refs/heads/*:refs/west/*` 全量拉？（`is_ancestor_of` 判断需要全部后代分支）
2. 默认策略为什么宁可 detach 也不动用户分支？
3. 实验 A 里为什么没有 `origin/main`？（显式 refspec，不建 remote-tracking）

---

# ⑬ 第 13 步：收尾——失败聚合与退出码

## 失败聚合

第 11 步循环里 `CalledProcessError` 全部收集进 `failed`；跑完所有项目后：

```python
# project.py:92-106
def _handle_failed(self, args, failed):
    if failed:
        names = [p.name for p in failed]
        if len(names) == 1:
            self.err(f'{names[0]} failed')
        else:
            self.err('multiple projects failed: ' + ', '.join(names))
        raise CommandError(1)          # ← 唯一的退出通道
```

**设计**：部分失败不中断整体（一个项目挂了不该拖累其余 50 个），最后统一结算。

## 顶层异常阶梯（main.py:578-641，挂在第 8 步的 try 外面）

```python
except KeyboardInterrupt:
    # Windows: exit(0xC000013A - 2**32)  （STATUS_CONTROL_C_EXIT 的 int32 表示）
    # POSIX:   恢复 SIG_DFL 后 os.kill(os.getpid(), SIGINT)
    #          → 正确的 130 退出码 + "向调用环境传达我死于信号"
    #          → while true; do west ...; done 整个循环一起退，而不是只退一次
except BrokenPipeError:
    sys.exit(0)                        # 配合管道 head 等场景
except CalledProcessError as cpe:
    self.cmd.err(f'command exited with status {cpe.returncode}: '
                 f'{quote_sh_list(cpe.cmd)}', fatal=True)
    sys.exit(cpe.returncode)           # 退出码 = git 的退出码
except ExtensionCommandError as ece:
    self.handle_extension_command_error(ece)   # 消息+hint；-vvv 打栈，否则落盘 traceback 文件
except CommandError as ce:
    sys.exit(ce.returncode)            # 命令自己的错误自己已打完，静默退
except MalformedManifest as mm:
    self.cmd.die(...)                  # ★update 特例：允许带着坏清单跑（第 9 步白名单的最终保障）
except WestNotFound as wnf:
    self.cmd.die(str(wnf))
```

POSIX 分支的注释（:606-617）值得整段读：re-raise SIGINT 而非简单 exit(130)，是为了**让 shell 感知"死于信号"**——这是对 CPython `exit_sigint()` 行为的纯 Python 复刻，注释里连 bug 编号（bpo-1054041）都给了。

## 完整的退出码语义

| 来源 | 退出码 |
|---|---|
| 全部成功 | 0 |
| 部分项目失败（_handle_failed） | 1（CommandError） |
| git 子进程失败冒泡 | git 的返回码（CalledProcessError） |
| 扩展命令失败 | ExtensionCommandError.returncode |
| Ctrl-C (POSIX) | 死于 SIGINT（通常表现为 130） |
| Ctrl-C (Windows) | 0xC000013A - 2**32 |
| 管道断裂 | 0 |

## 自测
1. 为什么 `_handle_failed` 要等全部项目跑完才抛？
2. POSIX 的 Ctrl-C 为什么不直接 `sys.exit(130)`？（shell 对"信号死亡"与"退出码死亡"的处理不同）
3. `MalformedManifest` 为什么单独捕获而不是归入 CommandError？（给 update 留修复通道）

---

# 附录 A：本流程串讲中发现的源码彩蛋（真 bug 两处）

| # | 位置 | 内容 | 触发条件 |
|---|---|---|---|
| 1 | project.py:1422 | `stats['get current status'] = perf_counter - start` 少了 `()` | `west update --stats --keep-descendants` 且命中保留分支路径 |
| 2 | project.py:1212 | `self.die("manifest repository {project.abspath} was deleted")` 缺 f 前缀 | 清单仓被删时，错误消息里原样显示 `{project.abspath}` 而非路径 |

# 附录 B：四份文档配合使用

```
你的位置                          用哪份
───────────────────────────────────────────────────────
入门：跟着实验场玩 + 六站阅读路线  《west源码阅读指南》
逐站精讲执行链路（本文）          《west命令执行全流程精讲》
要全局地图 / 快速回忆             《west实现机制图解》（16 图）
查证细节 / 行号证据               《west实现机制深度分析》
```

---

*实验环境：Ubuntu 22.04 / git 2.34 / west 1.4.0（pip 安装）+ 玩具工作区（3 bare 仓 + 本地清单仓）。全部命令与输出于 2026-10-09 实测；行号基于 commit `746e1b19`。*
