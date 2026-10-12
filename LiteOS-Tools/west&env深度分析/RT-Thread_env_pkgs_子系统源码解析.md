# RT-Thread env 工具包管理子系统深度源码解析

> 目标仓库：`~/workspace/repo/env`（v2.0.2，commit ec2c251）  
> 分析范围：以 `pkgs` 命令为核心的软件包安装、更新、卸载、镜像、数据库与 SCons 桥接机制  
> 约定：所有行为论断均标注 `file.py:line`；保留英文标识符不变。

---

## 1. 命令入口与完整命令面

### 1.1 入口脚本

仓库根目录的 `pkgs` 是一个 bash wrapper：

```bash
python3 ~/.env/tools/scripts/env.py package $*
```

它把 `package` 作为子命令传给 `env.py`（`pkgs:1-3`）。

在 `env.py` 中，顶层 `argparse` 注册了 `pkg` 子命令，并通过 `exec_arg('pkg')` 调用（`env.py:274-276`）。虽然 wrapper 传入的是 `package`，但 `cmds/cmd_package/__init__.py` 把子命令注册为 `'pkg'`，并设置 aliases `['pkgs', 'package']`（`__init__.py:64-69`），因此 `pkgs`、`pkg`、`package` 三个名字等价。

### 1.2 注册的所有 flag

`__init__.py:71-143` 注册的完整 flag 如下：

| 命令行 flag | 目标变量 | 对应处理函数 |
|-------------|----------|--------------|
| `--update` | `package_update` | `package_update()` |
| `--update-force` / `--force-update` | `package_update_force` | `package_update(True)` |
| `--list` | `list_packages` | `list_packages()` |
| `--wizard` | `package_create` | `package_wizard()` |
| `--upgrade` | `package_upgrade` | `package_upgrade()` |
| `--upgrade-force` / `--force-upgrade` | `package_upgrade_force` | `package_upgrade(force_upgrade=True)` |
| `--upgrade-script-force` | `package_upgrade_script_force` | `package_upgrade(force_upgrade=True, upgrade_script=True)` |
| `--upgrade-modules` | `package_upgrade_modules` | `package_upgrade_modules()` |
| `--printenv` | `package_print_env` | `package_print_env()` |

无任何位置参数；如果未提供任何 flag，`run_env_cmd` 会调用 `package_print_help()`，后者执行 `os.system('pkgs -h')`（`cmd_package_printenv.py:46-47`）。

---

## 2. `pkgs --update` 管线端到端

### 2.1 从 `.config` 读取用户选择

`package_update()` 首先调用 `pre_package_update()`（`cmd_package_update.py:1259`）。`pre_package_update()` 通过 `kconfig.parse(fn)` 解析当前目录下的 `.config`（`cmd_package_update.py:910-912`）。

`kconfig.py:51-96` 的解析逻辑：

- 逐行读取 `.config`。
- 只处理不以 `#` 开头且包含 `=` 的行。
- 键名以 `CONFIG_PKG_` 开头（`kconfig.py:72`）。
- 去掉前缀后：
  - 如果后缀是 `_PATH`，把 `CONFIG_PKG_<NAME>_PATH` 的值作为 `path`（去掉首尾引号）写入对应包（`kconfig.py:76-84`）。
  - 如果后缀是 `_VER`，把 `CONFIG_PKG_<NAME>_VER` 的值作为 `ver` 写入对应包（`kconfig.py:86-93`）。
- `CONFIG_PKG_USING_<NAME>=y` 形式的启用标志**被忽略**，没有收集任何信息（`kconfig.py:74-75` 仅设置了 `pkg_name` 但没有调用 `pkgs_path` 或 `pkgs_ver`）。

因此用户启用一个包时，`.config` 中必须同时出现：

```
CONFIG_PKG_USING_HELLO=y
CONFIG_PKG_HELLO_PATH="/packages/misc/hello"
CONFIG_PKG_HELLO_VER="v1.0.0"
```

解析结果是一个字典列表，每个元素形如 `{'name': 'HELLO', 'path': '/packages/misc/hello', 'ver': 'v1.0.0'}`（`kconfig.py:27-36, 39-48`）。注意 `name` 来自 `.config` 中的大写宏名，并非 `package.json` 中的 `name`；后续会通过读取 `package.json` 覆盖为真实包名（`cmd_package_list.py:53-65`）。

### 2.2 旧状态与新状态的获取

`pre_package_update()` 随后读取 `<bsp>/packages/pkgs.json` 作为 `oldpkgs`，并把当前 `.config` 解析结果作为 `newpkgs`（`cmd_package_update.py:924-925`）。返回的 `sys_value` 包含：

```
[oldpkgs, newpkgs, package_error, package_json_filename, pkgs_error_list_fn, bsp_packages_path, dbsqlite_pathname]
```

（`cmd_package_update.py:946`）。

### 2.3 版本到下载 URL 的映射

`install_package()` 中，先通过 `package_info['path']` 定位到索引中的 `package.json`：

```python
pkg_path = os.path.join(pkgs_root, pkg_path, 'package.json')
package.parse(pkg_path)
```

（`cmd_package_update.py:614-618`）。

然后调用 `package.get_url(package_info['ver'])` 获取 URL（`cmd_package_update.py:621`）。`PackageOperation.get_url(ver)` 在 `package.py:144-153` 中实现：遍历 `self.pkg['site']` 列表，按 `version` 字段（大小写不敏感）匹配，返回 `URL`。

`site` 字段是一个数组，每个元素的结构为：

```json
{
  "version": "v1.0.0",
  "URL": "...",
  "filename": "...",
  "VER_SHA": "..."
}
```

其中 `filename` 用于归档包（`package.py:173-178`），`VER_SHA` 用于 git 包（`package.py:155-160`）。如果 URL 以 `.git` 结尾，`is_git_url()` 判断为 git 包（`cmd_package_update.py:646, 684` 与 `cmd_package_update.py:479-489`）。

### 2.4 git 包安装流程

`install_git_package()`（`cmd_package_update.py:518-574`）执行：

1. 计算目标路径 `repo_path = <bsp>/packages/<name>-<ver>`（`cmd_package_update.py:522-532`）。
2. 如果目录已存在，直接返回 `True`，**不会重新安装或更新**（`cmd_package_update.py:534-536`）。
3. 执行 `git clone <package_url> <repo_path>`（`cmd_package_update.py:544-546`），默认全量克隆，无 `--depth`。
4. 进入包目录后执行：
   ```
   git remote set-branches origin <ver_sha>
   git fetch --depth 1 origin <ver_sha>
   git checkout -q <ver_sha>
   ```
   （`cmd_package_update.py:548-554`）。
5. 如果之前因为镜像切换了上游 URL，且 `url_origin` 是合法 git URL，则 `git remote set-url origin <url_origin>` 恢复 origin（`cmd_package_update.py:562-566`）。
6. 如果存在 `.gitmodules`，调用 `update_submodule()` 初始化子模块（`cmd_package_update.py:569-572`）。

`ver_sha` 的来源：

- 非镜像路径：从 `package.get_versha(package_info['ver'])` 读取 `package.json` 的 `VER_SHA`（`cmd_package_update.py:647`）。
- 镜像路径：从 `get_url_from_mirror_server()` 返回的 `get_ver_sha` 获得（`cmd_package_update.py:653-663`）。

### 2.5 归档包安装流程

非 git 包走 `install_not_git_package()`（`cmd_package_update.py:577-602`）：

1. `package.download(package_info['ver'], local_pkgs_path, package_url)` 下载到 `~/.env/local_pkgs/<filename>`（`cmd_package_update.py:580`，`package.py:169-234`）。
2. 下载完成后用 `archive.package_integrity_test()` 检查 zip/tar 完整性（`cmd_package_update.py:587-589`，`archive.py:181-208`）。
3. 调用 `archive.unpack()` 解压到 `<bsp>/packages`（`cmd_package_update.py:594`）。
4. `archive.unpack()` 内部先解压到临时目录 `<bsp>/packages/package_temp`，然后把顶层目录重命名为 `<package>-<version>`，再移动到目标位置（`archive.py:37-178`）。
5. 每个被解压的文件都会通过 `pkgsdb.save_to_database()` 把路径和 MD5 写入 SQLite，用于后续删除保护（`archive.py:82,135`，`pkgsdb.py:116-131`）。

---

## 3. `package.py` 理解的 `package.json` schema

`package.py:124-167` 的 `PackageOperation` 类只识别以下字段：

| 字段 | 用途 | 代码位置 |
|------|------|----------|
| `name` | 返回真实包名 | `package.py:134-135` |
| `site` | 版本列表 | `package.py:138-165` |
| `site[].version` | 版本匹配键 | `package.py:139,147,157` |
| `site[].URL` | 下载/克隆地址 | `package.py:148` |
| `site[].filename` | 归档包文件名（可选） | `package.py:173-178` |
| `site[].VER_SHA` | git 检出目标 commit/tag | `package.py:155-160` |

`cmd_package_wizard.py` 生成的 `package.json` 模板 `Package_json_file`（`package.py:86-119`）还包含以下字段，但 `PackageOperation` 并不读取：

- `description`, `description_zh`
- `enable`
- `keywords`
- `category`
- `author`（`name`, `email`, `github`）
- `license`
- `repository`
- `icon`
- `homepage`
- `doc`

`package.json` 中的 `repository` 字段在 `cmd_package_update.py:136-140` 被明确说明为“描述性元数据，不应被转换为 Git remote URL”；下载 URL 必须来自 `site[].URL`。

---

## 4. `pkgsdb.py`：SQLite schema 与文件 MD5 保护

### 4.1 数据库位置与表结构

数据库文件位于 `<bsp>/packages/packages.dbsqlite`（`cmd_package_update.py:899`）。建表 SQL 为：

```sql
CREATE TABLE packagefile
    (pathname TEXT, package TEXT, md5 TEXT);
```

（`cmd_package_update.py:906-908`）。

`pkgsdb.py` 提供的操作：

- `get_file_md5()`：计算文件 MD5（`pkgsdb.py:36-47`）。
- `save_to_database(pathname, package_pathname, before_change_name)`：插入一行记录（`pkgsdb.py:116-131`）。
- `remove_unchanged_file()`：比较数据库中的 MD5 与当前文件 MD5；若一致则删除并移除记录；若不一致则提示用户 `Press the Y Key to delete`（`pkgsdb.py:145-183`）。
- `deletepackdir()`：递归删除目录，对每个文件调用 `remove_unchanged_file()`（`pkgsdb.py:188-200`）。

### 4.2 文件 MD5 的用途

`pkgsdb` 只用于**归档包**的删除保护。当用户通过 `--update` 卸载一个 zip/tar 包时，系统会对比数据库中记录的原始 MD5。如果文件被修改过，则提示用户确认是否删除，避免误删用户改动（`pkgsdb.py:161-178`）。git 包的删除不走这个逻辑，而是直接删除整个 `.git` 目录（`cmd_package_update.py:1101-1134`）。

---

## 5. `<BSP>/packages/pkgs.json` 记录了什么

`pre_package_update()` 在 `<bsp>/packages` 不存在时会创建 `pkgs.json` 并写入 `[]`（`cmd_package_update.py:888-891`）。安装完成后，`install_packages()` 把当前选中的包列表写回该文件（`cmd_package_update.py:1244-1245`）。

`pkgs.json` 的每个元素即 `.config` 解析后的字典，典型格式：

```json
{
  "name": "hello",
  "path": "/packages/misc/hello",
  "ver": "v1.0.0"
}
```

它的作用是**持久化上一次更新的目标包状态**，下一次 `pkgs --update` 时：

- 与新的 `.config` 解析结果做集合差，决定需要卸载还是安装新包（`cmd_package_update.py:1265-1273`）。
- 作为“下载失败重试”的依据：如果某个包在磁盘上缺失，会被加入 `error_packages_list` 重新下载（`cmd_package_update.py:1036-1077`）。

---

## 6. SCons 桥接：安装后的包如何进入构建

`pre_package_update()` 会在 `<bsp>/packages` 下生成 `SConscript`（如果不存在）：

```python
import os
from building import *

objs = []
cwd  = GetCurrentDir()
list = os.listdir(cwd)

for item in list:
    if os.path.isfile(os.path.join(cwd, item, 'SConscript')):
        objs = objs + SConscript(os.path.join(item, 'SConscript'))

Return('objs')
```

（`package.py:39-51`）。

这个顶层 `SConscript` 会遍历 `<bsp>/packages` 下的每个子目录，只要子目录里有 `SConscript` 就将其纳入构建。因此每个被安装的包必须自带 `SConscript`，否则不会被构建。

对于 hal-sdk 包，还会生成一个桥接 `SConscript`，详见第 7 节。

---

## 7. hal-sdk 特殊处理

### 7.1 判定条件

hal-sdk 包在索引中的路径以 `packages/peripherals/hal-sdk/` 开头（`cmd_package_update.py:60,158-159`）。如果 BSP 根目录或其父级目录下存在 `libraries` 目录（大小写不敏感），则启用 hal-sdk 共享模式（`cmd_package_update.py:195-211`）。

### 7.2 安装路径

当启用 hal-sdk 共享时：

- 真实源码安装到 `<bsp>/libraries/<package>-<ver>`（`cmd_package_update.py:214-218, 673-676`）。
- 在 `<bsp>/packages/<package>-<ver>/SConscript` 生成桥接脚本 `HAL_SDK_BRIDGE_SCONSCRIPT`（`cmd_package_update.py:62-133`），该脚本运行时会在 `libraries` 中查找对应包的 `SConscript` 并返回构建对象（`cmd_package_update.py:62-133`）。

### 7.3 迁移逻辑

`migrate_hal_sdk_package_to_libraries()`（`cmd_package_update.py:264-289`）处理旧包迁移：

- 如果旧目录已经是桥接目录且源码已存在，直接删除桥接目录。
- 如果源码已存在，删除桥接目录。
- 否则把 `<bsp>/packages/<package>-<ver>` 移动到 `libraries` 下。

### 7.4 卸载逻辑

`remove_packages()` 中对 hal-sdk 包只删除 `<bsp>/packages/<package>-<ver>` 桥接目录，**不删除** `libraries` 下的真实源码（`cmd_package_update.py:1155-1163, 1181-1183`）。

---

## 8. `network.py` 中的镜像逻辑

### 8.1 镜像查询接口

镜像查询由 `cmds/cmd_package/cmd_package_utils.py:203-256` 的 `get_url_from_mirror_server()` 发起：

- 请求方法：`POST`。
- 请求 URL：`get_api_url('mirror_query')`，默认 `https://api.rt-thread.org/packages/queries`（`info.py:59-60`）。
- 请求体：
  ```json
  {
    "userName": "RT-Thread",
    "packages": [{"name": "<package_name>"}]
  }
  ```
- 返回结构（预期）：
  ```json
  {
    "packages": [
      {
        "packages_info": {
          "site": [
            {"version": "...", "URL": "...", "VER_SHA": "..."}
          ]
        }
      }
    ]
  }
  ```

函数按 `version` 匹配，返回 `(download_url, repo_sha)`。如果 URL 以 `.git` 结尾，还会返回 `VER_SHA`（`cmd_package_utils.py:243-247`）。如果返回空数组，提示包未在镜像服务器找到并回退到原始地址（`cmd_package_utils.py:235-237`）。

### 8.2 镜像选择策略

是否使用镜像由 `need_using_mirror_download()`（`cmd_package_update.py:430-476`）决定：

1. 读取 `~/.env/var/network.json` 中的 `download_server`；如果配置为 `gitee` 则使用镜像，配置为 `github` 则不用（`cmd_package_update.py:434-441`）。
2. 如果 `.env/tools/scripts/cmds/.config` 中定义了 `SYS_DOWNLOAD_SERVER_GITHUB` 或 `SYS_DOWNLOAD_SERVER_GITEE`，按配置决定（`cmd_package_update.py:447-453`）。
3. 如果没有配置，访问 `https://ifconfig.me/ip` 获取公网 IP，再调用 `http://www.ip-api.com/json/<ip>` 判断国家；如果是 `China` 则使用 Gitee 镜像（`cmd_package_update.py:460-466`）。
4. 如果 IP 查询失败，则根据时区判断：若 `(-time.timezone)/3600 == 8` 则使用 Gitee（`cmd_package_update.py:468-473`）。

该结果通过全局变量 `is_China_ip` 和 `mirror_settings_revision` 缓存，但**每次安装时仍可能访问网络**。

### 8.3 `network.request()` 的行为

`network.py:142-170` 的 `request()` 函数封装了 `requests.Session`：

- 从 `~/.env/var/network.json` 读取代理模式（`system`/`direct`/`custom`）和超时。
- 自动绕过 `localhost`、回环地址及 `no_proxy` 列表。
- 支持 `system` 模式读取系统代理、`custom` 模式使用配置代理、`direct` 模式禁用代理。
- 对 Git/pip 子命令，通过 `subprocess_environment()` 注入 `http.proxy` 等环境变量（`network.py:195-223`）。

---

## 9. `cmd_package_wizard.py` 向导生成什么

`package_wizard()`（`cmd_package_wizard.py:33-226`）在本地生成一个新包的**索引文件**，而不是可运行的源码包。流程：

1. 提示输入包名、版本、分类（支持 Arduino 特殊分类）、作者 GitHub ID、邮箱、许可证、仓库地址。
2. 创建以包名命名的目录。
3. 使用 `package.py` 中的 `Kconfig_file` 模板生成 `Kconfig`（`cmd_package_wizard.py:187-202`）。
4. 使用 `Package_json_file` 模板生成 `package.json`（`cmd_package_wizard.py:204-220`）。

默认 `package.json` 中的 `site` 包含两个版本：

- 一个归档版本（URL 为占位符 `https://<name>-<ver>.zip`）。
- 一个 `latest` git 版本（URL 为 `<repository>.git`，`VER_SHA` 为 `master`）。

向导不会自动推送到 `RT-Thread/packages` 索引仓库；它只是创建本地模板。

---

## 10. 失败处理

### 10.1 网络错误

- 镜像服务器不可达：`get_url_from_mirror_server()` 捕获异常，打印 `The mirror server could not be contacted`，返回 `(None, None)`，安装回退到原始 URL（`cmd_package_utils.py:253-256`）。
- 普通下载失败：`package.download()` 最多重试 5 次，超过后删除部分文件并返回 `False`（`package.py:217-230`）。
- `install_package()` 返回 `False` 后，`install_packages()` 把失败包加入 `packages_download_fail_list`，并提示用户再次运行 `pkgs --update`（`cmd_package_update.py:1226-1241`）。

### 10.2 缺少 `VER_SHA`

git 包安装需要 `ver_sha`。如果 `package.json` 中对应版本没有 `VER_SHA`，`package.get_versha()` 返回 `None`，随后 `git checkout -q None` 会失败，最终被 `except` 捕获并返回 `False`（`cmd_package_update.py:518-558`）。

### 10.3 版本冲突

代码没有“版本解析器”。如果 `.config` 中某个包的版本从 `v1.0.0` 变为 `v2.0.0`，`remove_packages()` 会卸载旧目录 `<name>-v1.0.0`，`install_packages()` 会安装新目录 `<name>-v2.0.0`（`cmd_package_update.py:1265-1273`）。

如果目标目录已存在（例如用户手动保留），git 包直接跳过安装（`cmd_package_update.py:534-536`）；归档包则可能在 `os.rename()` 或 `shutil.move()` 时失败。

---

## 11. 怪癖、Bug 与死代码

### 11.1 `pkgsdb.displaydir()` 的路径拼接 bug

```python
fi_d = os.path.join(filepath, fi)
pathname = os.path.join(filepath, fi_d)
```

（`pkgsdb.py:212-213`）。`pathname` 被重复拼接了一次，导致文件路径错误，MD5 校验和删除操作实际无法命中正确文件。

### 11.2 `kconfig.parse()` 忽略 `USING_`

`CONFIG_PKG_USING_<NAME>=y` 行只设置了局部变量 `pkg_name`，没有产生任何输出（`kconfig.py:74-75`）。这意味着解析逻辑假设 `PATH` 和 `VER` 一定存在，如果 Kconfig 配置不生成这两个宏，包将不会被安装。

### 11.3 `pre_package_update()` 目录切换不一致

创建 `<bsp>/packages` 时，代码先 `os.mkdir("packages")` 而不是 `os.mkdir(bsp_packages_path)`，紧接着 `os.chdir(bsp_package_path)`（`cmd_package_update.py:886-888`）。在多层目录或 Windows 下可能产生歧义，但通常 BSP 根目录下工作正常。

### 11.4 `is_user_mange_package()` 拼写与逻辑

函数名应为 `is_user_managed_package()`。它只检查 BSP `packages` 目录下第一层文件夹名是否匹配包名，且一旦匹配就 `break`（`cmd_package_update.py:409-417`）。如果用户改名或版本号导致目录名不匹配，就会误判为非用户管理包。

### 11.5 `update_latest_packages()` 对最新版本的更新脆弱

- 它只处理 `ver == "latest"` 或 `"latest_version"` 的包（`cmd_package_update.py:787`）。
- 如果镜像切换了 origin 但后续 `git_pull_repo()` 或子模块更新失败，origin 可能回不到原始 URL，造成状态不一致（`cmd_package_update.py:807-839`）。
- 对于非 git 的 latest 包，直接 `continue` 跳过，没有更新机制（`cmd_package_update.py:789-791`）。

### 11.6 `Bridge_SConscript` 命名冲突

模板中使用了 Python 内置名 `list` 作为变量名（`package.py:44`），虽然不影响运行时，但是不良实践。

### 11.7 `package_print_help()` 递归调用 shell

`cmd_package_printenv.py:46-47` 直接执行 `os.system('pkgs -h')`，如果 `pkgs` 脚本不在 `PATH` 中或出现循环，可能导致问题。

### 11.8 `rm_package()` 的 Windows 路径处理

Windows 下对 `dir_remove` 加了双引号后传给 `rd /s /q`，随后又判断 `os.path.isdir(dir_remove)`（`cmd_package_update.py:996-1016`）。如果第一次删除成功，第二次判断会失败并返回 `False`；但函数末尾只有在 `else` 分支返回 `True`。

### 11.9 `determine_url_valid()` 只检查 404

它把任何非 404 响应都视为 URL 有效（`cmd_package_update.py:391-402`），包括 403/500 等错误码。

---

## 12. 机制总结

### 12.1 关键设计决策

1. **以 `.config` 为唯一真相源**：`pkgs --update` 从 `CONFIG_PKG_<NAME>_PATH` 和 `CONFIG_PKG_<NAME>_VER` 推导目标包集合，而不是解析 `package.json` 或依赖 lockfile（`kconfig.py:72-93`）。
2. **包目录按 `<name>-<ver>` 命名**：每个版本对应一个独立文件夹，安装和卸载通过目录存在性和集合差决定（`cmd_package_update.py:518-536, 1101-1198`）。
3. **git 与归档包双轨制**：URL 以 `.git` 结尾即为 git 包，否则为归档包，分别走完全不同的下载、校验、解压和删除流程（`cmd_package_update.py:479-489, 577-602, 684-710`）。
4. **归档包使用 SQLite 文件级 MD5 保护**：安装时记录每个文件的 MD5，删除时对比，防止误删用户修改；git 包则直接整体删除（`pkgsdb.py:36-183`，`archive.py:82,135`）。
5. **镜像系统与上游恢复分离**：安装/更新时可能临时把 origin 切到镜像，完成后再恢复为 `package.json` 中的原始 URL（`cmd_package_update.py:562-566, 807-839`）。
6. **BSP 级共享 libraries 与桥接 SConscript**：hal-sdk 包源码放在 `libraries/` 共享，BSP `packages/` 下只保留桥接 SConscript，兼顾多 BSP 复用（`cmd_package_update.py:60-133, 195-289, 1155-1163`）。

### 12.2 与真正包管理器的差距

| 功能 | RT-Thread env pkgs | 真实包管理器（如 cargo/pnpm） |
|------|--------------------|------------------------------|
| lockfile | 无；只有 `<bsp>/packages/pkgs.json` 记录上一次状态（`cmd_package_update.py:888-891, 1244-1245`） | 有精确 lockfile |
| 依赖传递 | 无；不解析包之间的依赖关系 | 支持依赖树 |
| 版本冲突解决 | 通过目录名隔离，不能同时存在两个版本，无 SAT 求解 | 语义化版本与冲突解决 |
| 包卸载清理 | git 包直接删除；归档包按文件 MD5 提示用户 | 完整卸载脚本与反向依赖检查 |
| 校验和 | 仅检查 zip/tar 结构完整性，无加密哈希字段（`archive.py:181-208`） | sha256/sha512 校验 |
| 离线/缓存 | 归档包下载到 `~/.env/local_pkgs`，但没有索引缓存或包版本缓存 | 全局缓存与离线模式 |
| 镜像切换 | 运行时根据 IP/配置动态选择，URL 临时替换（`cmd_package_update.py:430-476`） | 配置化的 registry 切换 |

综上，`pkgs` 是一个面向嵌入式 BSP 的**轻量包分发器**，核心假设是每个包独立、版本与目录绑定、构建系统通过 `SConscript` 桥接。它不适合处理复杂依赖或作为通用包管理器使用。
