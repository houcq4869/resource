# west 实现机制图解

> 撰写日期：2026-10-09 ｜ 代码基线：west **v1.4.0**（`zephyrproject-rtos/west`，commit `746e1b19`）
> 源码位置：`~/workspace/repo/west`
> 本文是《west实现机制深度分析.md》的**图解配套版**：以图为主重建全部结论，行号引证与文字版一致。
> 图类型：mermaid 流程图 / 时序图 / 类图（VSCode、Typora、GitHub 可直接渲染）+ ASCII ref 空间图。
> 阅读路线：§1 总览 → §2 生命周期 → §3 Manifest（大脑）→ §4 命令层 → §5 扩展机制 → §6 配置 → §7 错误处理 → §8 设计评价。

---

## 1. 总体架构：一张图看懂 west 是什么

### 1.1 分层架构图

```mermaid
flowchart TB
    subgraph ENTRY["入口层"]
        EP["pyproject.toml<br/>west = west.app.main:main"]
        EM["__main__.py<br/>python -m west"]
    end

    subgraph APP["应用层 src/west/app/（命令编排）"]
        MAIN["main.py (1228行)<br/>WestApp：调度/扩展加载/别名"]
        PROJ["project.py (2331行)<br/>init/update/list/diff/status<br/>forall/grep/compare/manifest"]
        CFG["config.py (219行)<br/>west config"]
    end

    subgraph CORE["核心库层 src/west/（可独立 import）"]
        MAN["manifest.py (2784行) ★<br/>west.yml → Project 图"]
        CMD["commands.py (721行)<br/>WestCommand API<br/>+ 扩展命令工厂"]
        CONF["configuration.py (659行)<br/>三级配置"]
        UTIL["util.py<br/>west_topdir 发现"]
        LOG["log.py（遗留全局日志）"]
    end

    subgraph EXT["扩展命令（不在 west 仓！）"]
        ZEPH["zephyr 仓 scripts/west-commands.yml<br/>build/flash/debug/boards/sdk"]
        USER["用户自定义仓<br/>west-commands.yml"]
    end

    GIT["git（唯一外部进程依赖）"]

    ENTRY --> APP --> CORE
    EXT -. "惰性加载（§5）" .-> APP
    PROJ --> GIT
    MAN --> GIT
```

**要点**：
- west 本体 **不含任何构建逻辑**——`west build/flash/debug` 全部是 Zephyr 主仓通过扩展机制注入的（`main.py:1204-1225` 的 `BUILTIN_COMMAND_GROUPS` 里根本没有它们）。
- 核心依赖仅 4 个 Python 包：`colorama / PyYAML / pykwalify / packaging`。
- west = **YAML 声明的多仓拓扑执行器 + git ref 编排器 + 插件运行时**。

### 1.2 三个核心抽象（后文所有图围绕它们）

```mermaid
mindmap
  root((west 三大抽象))
    清单 Manifest
      west.yml 声明多仓拓扑
      import 递归合并
      先到先得优先级
    manifest-rev 引用
      refs/heads/manifest-rev
      清单意图 vs 本地工作解耦
    WestCommand
      do_add_parser / do_run 协议
      扩展命令即插件
```

---

## 2. 生命周期：从敲下 `west` 到命令执行

### 2.1 启动分发总流程（`WestApp.run`，main.py:235-278）

```mermaid
flowchart TD
    A["west &lt;cmd&gt; [args]"] --> B["main() :1196<br/>WestApp()"]
    B --> C["parse_early_args :94<br/>手工扫描 -h/-V/-v/-q/-z 与命令名<br/>（清单还没加载就能报对错误）"]
    C --> D{"west_topdir()<br/>util.py:65 向上找 .west"}
    D -->|"找到"| E["topdir = ..."]
    D -->|"未找到"| F["topdir = None<br/>（不算错误，看命令是否需要）"]
    E --> G["Configuration(topdir)<br/>三级配置对象 :262"]
    F --> G
    G --> H["load_manifest() :280<br/>失败不立刻死 → 存 self.mle 延迟处理（§7.2）"]
    H --> I["load_extension_specs() :388<br/>发现扩展，只建 stub（不 import）"]
    I --> J["load_aliases() / setup_parsers() :457<br/>内建真 parser + 扩展占位 parser"]
    J --> K["run_command() :534"]
    K -->|"命令名 ∈ builtins"| L["run_builtin :685"]
    K -->|"否则"| M["run_extension :700<br/>真正 import 扩展模块（§5）"]
    L --> N["cmd.run(args, unknown,<br/>topdir, manifest, config)<br/>commands.py:171"]
    M --> N
    N --> O["do_run(args, unknown)"]

    style D fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#ff9,stroke:#333,stroke-width:2px
    style M fill:#9ff,stroke:#333,stroke-width:2px
```

### 2.2 工作区发现算法（`west_topdir`，util.py:65-86）

```mermaid
flowchart TD
    A["cur = Path(cwd)"] --> B{"(cur/.west).is_dir()?"}
    B -->|"是"| C["return cur  ✅ 工作区根"]
    B -->|"否"| D{"cur == cur.parent?<br/>（到文件系统根了）"}
    D -->|"否"| E["cur = cur.parent<br/>继续向上"]
    E --> B
    D -->|"是"| F{"fall_back 且<br/>设置了 ZEPHYR_BASE?"}
    F -->|"是"| G["从 $ZEPHYR_BASE 重试一次<br/>fall_back=False（防无限递归）"]
    G --> B
    F -->|"否"| H["raise WestNotFound"]

    style C fill:#9f9
    style H fill:#f99
```

`.west/` 目录里只有两样东西：`config`（记录 `manifest.path`/`manifest.file`）和 init 过程的临时目录。

### 2.3 `WestCommand.run()` 状态注入契约（commands.py:171-200）

```mermaid
sequenceDiagram
    participant App as WestApp
    participant Cmd as WestCommand 子类
    participant Hook as pre-run hooks
    participant Sub as do_run()

    App->>Cmd: run(args, unknown, topdir, manifest, config)
    Note over Cmd: ① self.config = config（最先注入，die/color_ui 可用）
    Cmd->>Cmd: ② unknown 且未 accepts_unknown_args → parser.error
    Cmd->>Cmd: ③ topdir 为空且 requires_workspace → die
    Cmd->>Cmd: ④ self.topdir = fspath(topdir)；self.manifest = manifest
    loop 每个 hook
        Cmd->>Hook: hook(self)（延迟 IO：警告/清单错误都在这里吐）
    end
    Cmd->>Sub: do_run(args, unknown)
```

| 子类定制开关                 | 取值    | 使用者                                                                                      |
| ---------------------- | ----- | ---------------------------------------------------------------------------------------- |
| `accepts_unknown_args` | True  | Diff/Status/Grep（多余参数透传给 git/grep）                                                       |
| `requires_workspace`   | False | Init/Config/Help（可在工作区外运行）                                                               |
| `verbosity`            | INF 起 | 全部；`-v/-q` 经 `adjust_command_verbosity`（main.py:1182）平移，`-vvv` 时 `die()` 改抛 RuntimeError |

---

## 3. Manifest 子系统——west 的大脑（manifest.py）

### 3.1 数据模型类图（1.4.0 真实结构）

```mermaid
classDiagram
    class Manifest {
        +List~Project~ projects
        +ManifestProject manifest_project
        +List~str~ group_filter
        +from_topdir()$
        +from_file()$
        +from_data()$
        +get_projects(names, only_cloned)
        +is_active(project)
        +as_frozen_yaml()
    }
    class Project {
        +str name
        +str url
        +str revision
        +str path
        +str remote_name
        +SubmodulesType submodules
        +int clone_depth
        +WestCommandsType west_commands
        +List~str~ groups
        +abspath 懒缓存
        +posixpath 懒缓存
        +git(cmd, cwd, capture_stdout)
        +sha(rev)
        +is_cloned()
        +is_ancestor_of(rev, branch)
    }
    class ManifestProject {
        +str name = manifest
        +str url = 空串
        +str revision = HEAD
    }
    class Submodule {
        +str path
        +str name
    }
    class _import_ctx {
        +dict projects 先到先得
        +deque group_filter_q
        +list manifest_west_commands
        +imap_filter
        +path_prefix
        +project_importer
        +import_flags
    }
    class _import_map {
        +file
        +name_allowlist
        +path_allowlist
        +name_blocklist
        +path_blocklist
        +path_prefix
    }
    class _defaults {
        +remote
        +revision
    }

    Manifest "1" o-- "many" Project
    Manifest "1" o-- "1" ManifestProject : projects索引0固定
    Project "1" o-- "many" Submodule
    Manifest ..> _import_ctx : 递归构造时共享
    _import_map ..> Project : 过滤导入项目
    _defaults ..> Project : 提供默认值

    note for ManifestProject "FIXME #327：作者标注该类应当消失"
    note for _import_ctx "NamedTuple，但 projects 等<br/>字段是可变共享对象 ★"
```

**纠错提示**：此版本**没有** `Remote`/`Defaults`/`Import` 类——remote 只是 `{name: url-base}` 的 dict（manifest.py:2009-2010），defaults/import 分别是 `_defaults`/`_import_map` 两个 NamedTuple。数据模型全部用 NamedTuple，不用 dataclass。

### 3.2 west.yml → 对象的解析流水线

```mermaid
flowchart LR
    A["west.yml 文件"] --> B["yaml.load<br/>SafeLoader/CSafeLoader :211"]
    B --> C{"有顶层 'manifest' 键?<br/>:560"}
    C -->|"否"| X1["MalformedManifest"]
    C -->|"是"| D["version 预检查 :568<br/>对照 SCHEMA_VERSION='1.2'<br/>+ _VALID_SCHEMA_VERS 白名单"]
    D -->|"过/不过"| E["pykwalify.Core<br/>.validate() :595<br/>外部 schema 文件<br/>manifest-schema.yml"]
    E -->|"SchemaError"| X2["MalformedManifest<br/>（附文件路径+schema 路径）"]
    E -->|"通过"| F["语义解析<br/>_load_validated :1992"]
    F --> G["_load_self :2106<br/>→ ManifestProject"]
    F --> H["_load_defaults :2282<br/>→ _defaults"]
    F --> I["_load_projects :2294<br/>逐项目 _load_project :2337<br/>→ Project（URL/路径计算）"]
    I --> J["有 import: 的项目<br/>→ _import_from_project :2509"]
    G --> K["self: import: 有内容?<br/>→ _import_from_self :2152"]
    J --> L["递归解析（§3.4）"]
    K --> L
    L --> M["_check_paths_are_unique :2728<br/>ManifestProject 插入索引 0<br/>→ self._projects"]

    style E fill:#ff9
    style L fill:#f9f
```

URL 计算的严格优先级（`_load_project` :2351-2377）：

```
url 显式给出 ────────────► 直接用（remote/repo-path 互斥报错）
否则 remote 给出 ────────► url = url_bases[remote] + '/' + (repo-path | name)
否则 defaults.remote ────► 同上（继承默认 remote）
都没有 ─────────────────► MalformedManifest
```

### 3.3 校验的三个"刻意的洞"

| 字段 | schema 声明 | 原因 |
|---|---|---|
| `import` | `type: any` | 递归语义运行时细查（str/list/dict/bool） |
| `submodules` | `type: any` | bool 或 list[dict] 两种形态 |
| `west-commands` | `type: str` | list 只会在 **import 合并时内部产生**，YAML 里直接写 list 会被拒 |

### 3.4 import 递归解析——west 最精巧的算法 ★★★

**机制：递归构造新 Manifest 实例 + 共享同一个可变 `_import_ctx`。**

```mermaid
flowchart TD
    subgraph TOP["顶层 Manifest"]
        A["解析 west.yml"] --> B{"遇到 import:"}
        B -->|"self: import: str"| C["_import_path_from_self :2202<br/>文件系统读取（文件或目录下全部 *.yml 按序）"]
        B -->|"self: import: dict"| D["_import_map_from_self :2244"]
        B -->|"项目 import: bool/str"| E["_import_from_project :2509<br/>True → 读该项目的 west.yml"]
        B -->|"项目 import: dict"| F["_import_map_from_project :2556"]
    end

    C & D & E & F --> G{"项目已克隆且<br/>非 FORCE_PROJECTS?"}
    G -->|"是"| H["从 git manifest-rev 读<br/>_manifest_content_at :252<br/>git ls-tree rev path<br/>blob→文件内容 / tree→目录全部 *.yml"]
    G -->|"否"| I["project_importer 回调<br/>（update 命令注入：先 update 再取内容）"]
    H & I --> J["child_ctx = ctx._replace(<br/>  path_prefix 累积拼接,<br/>  imap_filter 逻辑与合成,<br/>  current_data=新内容,<br/>  manifest_west_commands=[]<br/>) :2583"]

    J --> K["Manifest(topdir, internal_import_ctx=child_ctx)<br/>★ 新实例，但 ctx.projects 等<br/>★ 字段与父级共享同一对象"]
    K --> L{"_add_project :2690<br/>name in ctx.projects?"}
    L -->|"否（先到）"| M["写入共享 dict ✓<br/>→ 该项目存活"]
    L -->|"是（后到）"| N["忽略 ✗<br/>→ 先 import 的定义胜出"]
    K --> O["子清单的 west-commands<br/>merge 进导入者 project :2606<br/>子 group_filter appendleft 入队"]
    K --> P{"更深层的 import?"}
    P -->|"是"| J
    P -->|"递归过深"| Q["RecursionError →<br/>_ManifestImportDepth :686<br/>（无显式环检测！）"]

    style K fill:#f9f,stroke-width:3px
    style M fill:#9f9
    style N fill:#f99
```

**最终项目顺序**（`_load_validated` :1992-1999 文档明确）：

```
projects[0] = ManifestProject（清单仓自身）
    ↓ 之后依次：
① self: import: 导入的项目      ← 优先级最高
② 本清单 projects: 声明的项目
③ 项目 import: 导入的项目       ← 优先级最低
```

### 3.5 import 过滤器：allow/block 决策图（`_is_imap_ok` :337-353）

```mermaid
flowchart TD
    A["候选项目 (name, path)"] --> B{"命中黑名单?<br/>name in blocklist 或<br/>path.match(任一 pattern)"}
    B -->|"是"| C{"命中白名单?<br/>name/path allowlist"}
    C -->|"是"| D["✅ 导入（白名单豁免黑名单）"]
    C -->|"否"| E["✗ 拒绝"]
    B -->|"否"| F{"存在任何白名单?"}
    F -->|"是"| G{"命中白名单?"}
    G -->|"是"| D
    G -->|"否"| E
    F -->|"否（无白名单）"| H["✅ 导入（默认全放行）"]

    style D fill:#9f9
    style E fill:#f99
    style H fill:#9f9
```

补充规则：嵌套 import 的过滤器做**逻辑与**（`_compose_imap_filters` :434-445）；`path-prefix` 沿 import 链**逐层累积拼接**（:2253, :2585）；旧名 `whitelist/blacklist` 仍兼容（:2643-2655）。

### 3.6 两组过滤机制对比（易混淆）

```mermaid
flowchart LR
    subgraph GF["group-filter（按组）"]
        A1["来源：清单 group-filter:<br/>+ 配置 manifest.group-filter"]
        A2["deque appendleft 入队 :2056"]
        A3["_final_group_filter :2741<br/>按队列序应用禁用组<br/>→ 更早 import 的清单胜出"]
    end
    subgraph PF["project-filter（按名，覆盖层）"]
        B1["来源：仅配置<br/>manifest.project-filter"]
        B2["+regex/-regex 逗号分隔<br/>last-match-wins :137-171"]
        B3["is_active :1720<br/>优先级高于 group 判定"]
    end
    GF --> R["Manifest.is_active(project)"]
    PF -->|"压过 group"| R
```

---

## 4. 命令层：init 与 update 的 git 编排

### 4.1 先看灵魂：manifest-rev 解耦模型（ASCII ref 空间图）

west 从不把清单 revision 直接 checkout 到分支。每个项目仓里有**三个互不干扰的空间**：

```
 项目仓（例：zephyr/）的 git ref 空间
 ┌────────────────────────────────────────────────────────────────┐
 │                                                                │
 │  refs/heads/manifest-rev ──► ● C4   「清单意图」                │
 │                                │\         west update 唯一维护   │
 │                                │ ● C5   refs/west/*             │
 │                                │          （fetch 中间态，        │
 │  refs/west/heads/main ──► ● C3 │           用完即删）            │
 │                                │                                │
 │  HEAD (detached) ──────► ● C2  「用户工作」                      │
 │  refs/heads/my-branch ─► ● C1 ─┘       完全归用户                │
 │                                                                │
 └────────────────────────────────────────────────────────────────┘

 west update 时：
   fetch → 写 refs/west/*（SHA 时用 'refs/heads/*:refs/west/*' 全量保存分支）
         → update-ref refs/heads/manifest-rev <目标SHA>   （原子移动意图指针）
         → 逐个删 refs/west/*                              （清理中间态）
   然后基于「用户 HEAD 与 manifest-rev 的祖先关系」决定要不要动工作区（§4.3）
```

**这就是 west 多仓模型不破坏本地工作的根基**：意图（manifest-rev）、中间态（refs/west）、用户工作（HEAD/分支）三者分离。

### 4.2 `west init` 两种模式（project.py:146-413）

```mermaid
flowchart TD
    A["west init"] --> B{"-l/--local?"}
    B -->|"是（围绕已有检出）"| C["local() :263"]
    C --> C1["manifest_dir = 已有目录"]
    C1 --> C2["topdir = manifest_dir.parent<br/>创建 topdir/.west"]
    C2 --> C3["写配置 manifest.path/file<br/>（零 git 操作！）"]
    B -->|"否（URL 引导）"| D["bootstrap() :294"]
    D --> D1["文件系统探测 :320<br/>建空目录→rename→rmtree<br/>（clone 前快速失败，NTFS #558）"]
    D1 --> D2["git clone [--branch mr] [--depth n]<br/>url → .west/manifest-tmp"]
    D2 --> D3{"验证 manifest 文件存在?<br/>Manifest.from_data(<br/>ImportFlag.IGNORE) 解析 self:path<br/>:362"}
    D3 -->|"有"| D4["shutil.move(tmp → topdir/manifest_path)"]
    D3 -->|"无"| X["die"]
    D4 --> D5["写配置 manifest.path/file"]

    style C3 fill:#9f9
    style D2 fill:#ff9
```

`.west/` 布局：`config`（本地配置）+ `manifest-tmp`（init 临时目录，用完移走）。项目仓的克隆不属于 init，属于 update。

### 4.3 `west update` 每项目 git 序列（project.py:1376-1457）

```mermaid
flowchart TD
    A["update_all :1178<br/>重新解析清单（FORCE_PROJECTS<br/>+ update_importer 递归拉取 import 内容）"] --> B["遍历 active 且非 ManifestProject<br/>且未更新过的项目"]
    B --> C["ensure_cloned :1489"]
    C -->|"未克隆"| C1["git init [--initial-branch=init_placeholder]<br/>+ git remote add origin url<br/>（≥2.28 才有 --initial-branch）"]
    C --> D["set_new_manifest_rev :1588"]
    D --> D1{"smart 策略：revision<br/>是本地已有 tag/commit?"}
    D1 -->|"是"| D2["免 fetch！直接 update-ref<br/>manifest-rev = revision^commit"]
    D1 -->|"否"| E["fetch :1602"]
    E --> E1{"revision 是 SHA?"}
    E1 -->|"是且非 narrow"| E2["refspec: refs/heads/*:refs/west/*<br/>（保存全部分支，供后代判断）"]
    E1 -->|"否"| E3["直接 fetch revision<br/>目标取 FETCH_HEAD^commit"]
    E2 & E3 --> E4["git update-ref -m 'west update: ...'<br/>refs/heads/manifest-rev &lt;sha&gt; :2136"]
    E4 & D2 --> F["clean_refs_west :1668<br/>逐个 update-ref -d refs/west/*"]
    F --> G["ensure_head_ok :1689<br/>HEAD 损坏 → checkout --detach manifest-rev"]
    G --> H["decide_update_strategy :1732<br/>当前分支？manifest-rev 是其祖先?"]
    H --> I{"策略"}
    I -->|"--keep-descendants<br/>且是祖先 ★最高优先级"| J["什么都不做<br/>（保留你的后代分支）"]
    I -->|"--rebase 且在分支上"| K["git rebase refs/heads/manifest-rev"]
    I -->|"默认"| L["git checkout --detach &lt;sha&gt;"]
    J & K & L --> M["update_submodules :1324<br/>sync --recursive +<br/>update --init [--rebase] --recursive"]
    M --> N["下一个项目（失败不中断，聚合处理）"]

    style E4 fill:#ff9,stroke-width:2px
    style J fill:#9f9
```

三条关键规则：
1. **update 从不修改清单仓本身**（跳过 ManifestProject，:1196/:1268）。
2. **失败聚合不中断**：逐项目捕获 `CalledProcessError`，跑完全部后 `_handle_failed`（:92-106）统一抛 `CommandError(1)`。
3. **自修复通道**：main.py:316-317 把 `update` 列入 `no_manifest_ok` 白名单——清单本身损坏时仍允许运行 update 来修复（:633-639 专门捕获 `MalformedManifest`）。

### 4.4 其他命令实现速览

| 命令 | 图示要点 | 关键引证 |
|---|---|---|
| `forall` | 串行执行！`Popen(cmd, shell=True).wait()` 朴素循环；注入 `WEST_PROJECT_NAME/PATH/ABSPATH/REVISION/URL/REMOTE` 环境变量 | project.py:1820-1843 |
| `list` | 惰性求值：`sha/cloned/active` 字段用 DelayFormat+thunk，`-f` 没用到就不算 | :483-506 |
| `diff` | `--src-prefix={path}/` 改写前缀；rc=1 **或** rc=0 但有输出都算有差异（兼容 merge-conflict） | :914-978 |
| `status` | 先跑 `git status --porcelain` 0.1s 超时探测，非空才真跑（省时） | :116-144 |
| `compare` | HEAD vs manifest-rev 三重比较：分支名/SHA/dirty；需 git≥2.22 | :752-912 |
| `manifest --freeze` | 每项目解析 manifest-rev 的 SHA，生成可复现清单 | manifest.py:1629-1664 |
| `manifest --untracked` | 顶层目录游走（项目路径排序处理嵌套），列出未跟踪路径 | :681-743 |

**注意**：`forall` 在 1.4.0 **没有并行**；`list` **没有 `--group` 选项**（组过滤经 `is_active` 隐式生效，`-g` 是 forall 的）。

---

## 5. 扩展命令机制：west 的插件运行时 ★

### 5.1 从 west-commands.yml 到可执行命令的全流水线

```mermaid
flowchart TD
    A["manifest.projects[].west_commands<br/>（west-commands: 字段，import 会合并）"] --> B["extension_commands() :604<br/>commands.allow_extensions=false 可整体禁用"]
    B --> C["_ext_specs() :633 逐文件处理"]
    C --> C1["escapes_directory 防目录逃逸"]
    C1 --> C2{"文件存在?"}
    C2 -->|"否（项目未克隆）"| C3["跳过（不算错误）"]
    C2 -->|"是"| C4["yaml SafeLoader 解析<br/>→ pykwalify 校验<br/>west-commands-schema.yml"]
    C4 --> D["_ext_specs_from_desc :672<br/>每个命令条目 → WestExtCommandSpec(<br/>name, project, help, _ExtFactory)<br/>★ 工厂惰性：此时不 import 任何模块"]
    D --> E["main.load_extension_specs :388"]
    E --> E1{"名字影子化内置命令?"}
    E1 -->|"是"| E2["丢弃 + queued_io 排队警告"]
    E1 -->|"否"| E2b{"扩展间重名?"}
    E2b -->|"是"| E2
    E2b -->|"否"| F["登记 self.extensions[name]<br/>+ setup_parsers 建 stub parser<br/>（add_parser(name, add_help=False)）"]
    F --> G["用户实际选中该命令时<br/>run_extension :700"]
    G --> H["factory() 触发 import<br/>_commands_module_from_file :694"]
    H --> H1["py 文件目录追加进 sys.path<br/>（扩展可带兄弟模块）"]
    H1 --> H2["spec_from_file_location<br/>合成名 west.commands.ext.cmd_N<br/>（按路径缓存）"]
    H2 --> H3["getattr(mod, class 或 name)<br/>→ cls() 无参构造 ★隐式契约"]
    H3 --> I["重建全新 parser 树 → add_parser<br/>→ 重新 parse_known_args"]
    I --> J["set_zephyr_base :742（源码自标注 HACK）<br/>→ cmd.run(...)"]

    style D fill:#ff9
    style H3 fill:#f9f
```

### 5.2 west-commands.yml 的 schema（west-commands-schema.yml:13-37）

```yaml
west-commands:
  - file: scripts/west_commands/build.py   # 必填
    commands:                              # 必填
      - name: build                        # 缺省时 name/class 互为默认
        class: Build                       # 缺省 = name
        help: 编译应用程序                   # 缺省 = "(no help provided; ...)"
```

### 5.3 三态 extensions 与 help 的关系

```
self.extensions 的取值      含义                        west help 表现
─────────────────────────────────────────────────────────────────
None                        清单本身加载失败            "Cannot load extension commands; ..."
{}                          清单正常，但无扩展命令      只列内建命令
{名字: spec, ...}           正常                       按项目分组列出扩展命令
```

`west help <ext-cmd>` 的实现是借道执行 `run_extension(name, [name, '--help'])`（main.py:861-903）。

---

## 6. 配置系统（configuration.py）

### 6.1 三级配置与优先级

```mermaid
flowchart TB
    subgraph LOC["LOCAL（最高优先级）"]
        L["&lt;topdir&gt;/.west/config<br/>env: WEST_CONFIG_LOCAL"]
    end
    subgraph GLOB["GLOBAL"]
        G["~/.westconfig<br/>或 $XDG_CONFIG_HOME/west/config<br/>env: WEST_CONFIG_GLOBAL"]
    end
    subgraph SYS["SYSTEM（最低）"]
        S["Linux/BSD: /etc/westconfig<br/>macOS: /usr/local/etc/westconfig<br/>Win: ProgramData/west/config<br/>env: WEST_CONFIG_SYSTEM"]
    end
    LOC -->|"读：_whence = [local, global, system]<br/>取第一个命中 :228-253"| READ["读默认 ALL"]
    GLOB --> READ
    SYS --> READ
    WRITE["写默认 LOCAL<br/>（懒建文件 _create :299）"] -.->|"set/append 默认"| LOC

    style LOC fill:#9f9
    style WRITE fill:#ff9
```

**关键事实**：
- 与 `git config` **零交互**——只借用其"文件位置 + 优先级"惯例，全库无 `git config` 子进程。
- `_InternalCF` 包装 `configparser(allow_no_value=True)`，`section.key` 在首个 `.` 切分；**每次 set 立即全量重写文件**（无事务，多进程并发写会互踩）。
- 读写不对称：**读默认 ALL，写默认 LOCAL**。
- 遗留双轨：`log.py` 全局 VERBOSE（issue #149，v2.0 移除）+ 模块级 `read_config/update_config` 旧 API 发 DeprecationWarning。

---

## 7. 子进程与错误处理

### 7.1 git 调用模式（Project.git，manifest.py:910-974）

```
                    ┌──────────────────────────────────────────┐
  命令构造           │ args = ['git'] + cmd_list + extra_args   │
                    │ （永远是 argv 列表，无 shell！）           │
                    └──────────────┬───────────────────────────┘
                                   ▼
        Popen(args, cwd=项目abspath, stdout/stderr 按需 PIPE)
                                   ▼
     ┌────────────────────────────┴────────────────────────────┐
     │ shlex.quote 的两个真实用途（都只是"显示"）：              │
     │  ① 字符串命令的 shlex.split 预拆（POSIX 规则）           │
     │  ② 日志/错误信息里的人类可读还原 quote_sh_list           │
     └────────────────────────────────────────────────────────┘

  全库唯一 shell=True：forall（它本来就是让用户跑任意 shell 命令的）
```

### 7.2 延迟清单错误——"坏清单也能跑对命令"的机制

```mermaid
flowchart TD
    A["load_manifest() :280 抛异常"] --> B["不立刻 die！<br/>存 self.mle"]
    B --> C["命令是 help/config/topdir/<br/>init/manifest/update?<br/>（no_manifest_ok 白名单 :316）"]
    C -->|"否"| D["handle_builtin_manifest_load_err :305<br/>按异常类型生成诊断 → die"]
    C -->|"是"| E["诊断消息包成闭包<br/>→ queued_io 排队"]
    E --> F["挂为 pre-run hook<br/>（在命令自己的 verbosity 上下文里输出）"]
    F --> G["命令正常执行<br/>（update 甚至能修复坏清单）"]

    style B fill:#ff9
    style G fill:#9f9
```

### 7.3 顶层异常 → 退出码映射（main.py:578-641）

```
KeyboardInterrupt     → Windows: exit(0xC000013A - 2**32)
                        POSIX:   恢复 SIG_DFL 后 re-raise SIGINT（还原信号语义）
BrokenPipeError       → exit(0)（配合管道 head 等）
CalledProcessError    → "command exited with status N: <quoted cmd>"，exit(N)
ExtensionCommandError → 消息 + hint；-vvv 打栈，否则落盘 traceback 文件，exit(rc)
CommandError          → 静默 exit(ce.returncode)
MalformedManifest     → cmd.die（update 例外见 §4.3）
WestNotFound          → die
die() 内部            → -vvv 时改抛 RuntimeError（逼出完整栈）
```

部分失败策略（update/status/diff/compare/forall/grep 统一）：**继续跑完 → 末尾聚合 → `CommandError(1)`**。

---

## 8. 设计评价一图流

```mermaid
quadrantChart
    title west 设计决策定位（主观评估）
    x-axis 实现朴素 --> 实现精巧
    y-axis 局部取舍 --> 架构价值
    manifest-rev 解耦模型: [0.85, 0.95]
    共享ctx的import解析: [0.90, 0.85]
    惰性扩展加载: [0.75, 0.70]
    延迟清单错误: [0.70, 0.65]
    forall串行执行: [0.15, 0.25]
    RecursionError兜底环检测: [0.20, 0.30]
    配置立即全量重写: [0.25, 0.35]
```

### 亮点

1. **manifest-rev 三空间解耦**（§4.1）：意图/中间态/用户工作分离，`west update` 永不破坏本地工作——整个工具的灵魂。
2. **共享可变 ctx + 先到先得**（§3.4）：三条朴素规则（递归构造、单一 dict、首写胜出）导出全局一致的优先级语义，west-commands 合并与 group-filter 优先级全部对齐。
3. **惰性扩展加载**（§5.1）：stub 占位 → 选中才 import → 重建 parser，大清单下启动开销可控。
4. **工程细节**：init 前文件系统探测、status 0.1s 探测、list thunk 惰性求值、diff 对 merge-conflict 返回码的兼容。

### 不足与 quirks

| # | 问题 | 引证 |
|---|---|---|
| 1 | 无显式 import 环检测，靠 `RecursionError` 兜底（作者自认 hack） | manifest.py:686-688 |
| 2 | `CommandContextError` 定义导出但全库从未 raise | commands.py:62 |
| 3 | `log.py` 全局状态双轨制，v2.0 才清理（issue #149） | log.py:6-20 |
| 4 | `forall` 串行 + `shell=True`（注入面靠文档约束） | project.py:1839 |
| 5 | `ManifestProject` 被标记"该类应当消失"（#327），projects[0] 特判遍布各命令 | manifest.py:1106 |
| 6 | `_commands_module_from_file` 缓存键不一致（查找用 resolve 后路径，写入用原始路径） | commands.py:712/:719 |
| 7 | 配置写为立即全量重写，无并发保护 | configuration.py:105-114 |

---

## 9. 一页速查（TL;DR）

```
west = YAML 声明的多仓拓扑执行器 + git ref 编排器 + 插件运行时

  west.yml ──pykwalify──► Manifest ──import递归(共享ctx,先到先得)──► Project 图
                                                                    │
  west update：fetch → refs/west/* → update-ref manifest-rev → 清理   │
              → keep-descendants/rebase/checkout → submodules        │
                                                                    ▼
  领域命令(build/flash/...)：zephyr 仓 west-commands.yml ──惰性工厂──► WestCommand 插件

  骨架 8300 行：manifest.py(2784) > project.py(2331) > main.py(1228)
  依赖 4 个：colorama / PyYAML / pykwalify / packaging
  两把钥匙：manifest.py 的 import 解析 + project.py 的 update git 序列
```

---

*本文所有行号基于 west v1.4.0（commit 746e1b19）；文字论证与实操验证见同目录《west实现机制深度分析.md》。*
