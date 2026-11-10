# SmartGit 独立工具

Linux 下运行的 SmartGit 26.1 独立工具，使用 Python 3 标准库，无需安装 Python 包。隐私启动功能额外需要 `bwrap`（Bubblewrap）和 Bash，并要求系统允许创建用户、挂载和 PID 命名空间。

## 环境与工程完整性

- 运行环境：Linux、Python 3；两个脚本只使用标准库，无需构建或安装 Python 包。
- 专用 ID 启动器还需要 Bash、`bwrap`（Bubblewrap）、`readlink`、`cmp` 等系统命令，以及可用的用户、挂载和 PID 命名空间。安装时会实际运行映射探测，失败即停止安装。
- SmartGit 必须安装在 `/usr/share/smartgit/bin/smartgit.sh`，并提供 `/usr/share/applications/syntevo-smartgit.desktop`。当前没有自定义安装路径参数。
- 使用当前桌面用户运行安装命令，无需 `sudo`。设置 `XDG_CONFIG_HOME` 或 `XDG_DATA_HOME` 时必须使用绝对路径，并在安装、检查和卸载时保持一致。
- 申请 evaluation 需要访问官方 HTTPS 服务；验证已有文件可以离线完成。

工程包含两个独立 CLI、安装器回归测试和可选 Bun 快捷命令，主要功能链路已经实现。当前测试覆盖安装器的重复安装与恢复、命名空间失败时保留配置、无效 ID、保护非托管包装器、无原桌面入口时的卸载，以及旧入口清理和文件保留行为。

完整性限制：evaluation 的签名、绑定、有效期和文件保存流程尚无自动化测试；安装器测试模拟了子进程调用，未验证真实 Bubblewrap 映射或 SmartGit GUI 集成。自动化测试通过不代表官方服务可用或当前主机允许命名空间。当前没有 CI 配置或发行打包流程。

## 快速开始：安装专用 ID 启动器

在本目录运行：

```bash
python3 smartgit_private_id.py install
python3 smartgit_private_id.py check
```

安装会生成固定的专用 ID 和隔离启动包装器，再添加用户级桌面入口。退出所有 SmartGit 进程后，从应用菜单启动。脚本不会自动启动 SmartGit，也不会更改系统 machine-id 或现有授权文件。

安装成功后会自动删除指向同一包装器的两个旧入口：`${XDG_DATA_HOME:-$HOME/.local/share}/applications/smartgit-private.desktop` 和 `$HOME/Desktop/SmartGit-Private.desktop`，应用菜单保留当前的 `SmartGit` 入口。指向其他程序的同名文件会保留；安装探测失败时不会清理旧入口。清理失败会输出警告，可在解决权限问题后重新运行 `install`。

也可以在终端使用同一包装器启动 SmartGit，并传入应用参数：

```bash
private_launcher="${XDG_CONFIG_HOME:-$HOME/.config}/smartgit-private/launch"
"$private_launcher"
```

直接运行系统的 `smartgit` 命令或 `/usr/share/smartgit/bin/smartgit.sh` 不会经过此包装器。`check` 成功时输出 `Private machine-id mapping verified`，不会启动 SmartGit。

## 固定的应用专用 machine-id

```bash
# 首次安装生成随机 ID，重复安装保留已有 ID。
python3 smartgit_private_id.py install

# 显式设定固定 ID，必须是 32 位小写十六进制。
# 此操作会替换已有专用 ID，可能影响现有机器绑定凭证。
python3 smartgit_private_id.py install --machine-id 0123456789abcdef0123456789abcdef

# 检查读取路径，不启动 SmartGit。
python3 smartgit_private_id.py check

# 恢复原有用户级桌面入口，保留专用 ID 和包装器。
python3 smartgit_private_id.py uninstall
```

安装文件位于 `${XDG_CONFIG_HOME:-$HOME/.config}/smartgit-private/`：

- `machine-id`：固定的专用标识，权限 `0600`。
- `launch`：使用 Bubblewrap 的启动包装器。
- `original.desktop`：原用户级桌面入口的备份（原本存在时）。

`launch` 的权限为 `0700`，桌面入口备份的权限为 `0600`。重复安装更新包装器和桌面入口，默认保留已有 ID。安装会拒绝覆盖非本工具管理的包装器；已有备份且用户桌面入口被外部修改时，也会停止重装。

桌面入口位于 `${XDG_DATA_HOME:-$HOME/.local/share}/applications/syntevo-smartgit.desktop`。当前支持的系统安装路径是 `/usr/share/smartgit/bin/smartgit.sh`。

包装器在进程自己的挂载命名空间中替换 `/etc/machine-id`、存在的 `/var/lib/dbus/machine-id` 和 `/etc/hostid`，系统文件保持不变。已有机器绑定凭证可能需要重新激活。包装器属于文件视图替换，**不是完整的隐私沙箱**；其他主机文件、设备、D-Bus 和网络仍可访问，其他应用不受影响。

`uninstall` 仅恢复原有用户桌面入口（没有备份时删除托管入口），保留 `machine-id` 和 `launch`，因此已有终端调用仍然可用。恢复成功后会移除已使用的桌面入口备份；若当前入口不受本工具管理则拒绝操作。

## 请求官方签发的 evaluation

```bash
# 使用真实系统标识申请；父目录必须存在，目标文件必须尚不存在。
python3 smartgit_evaluation.py request --output /tmp/smartgit.evaluation

# 离线验证刚保存的凭证。
python3 smartgit_evaluation.py verify /tmp/smartgit.evaluation

# 也可以验证已有的 SmartGit evaluation 文件。
python3 smartgit_evaluation.py verify "$HOME/.config/smartgit/26.1/evaluation"
```

使用专用 ID 时，请通过同一个包装器运行请求和验签。安装包装器后，在本工程目录执行：

```bash
private_launcher="${XDG_CONFIG_HOME:-$HOME/.config}/smartgit-private/launch"
"$private_launcher" --exec python3 "$PWD/smartgit_evaluation.py" request --output /tmp/smartgit-private.evaluation
"$private_launcher" --exec python3 "$PWD/smartgit_evaluation.py" verify /tmp/smartgit-private.evaluation
```

请求发送至 `https://license.syntevo.com/v1/evaluate`，包含产品、主版本、Build、操作系统和机器标识摘要。默认 Build 为 `261056`，可通过 `request --build <build>` 指定其他 26.1 构建。`umi` 是本机 ID 内容的 SHA-512 摘要前 12 字节经过自定义 Base61 编码的结果，不上传原始 ID。

成功响应先通过主签名、正文签名、产品、版本、机器绑定及有效期检查，再以 `0600` 权限保存原始字节。脚本拒绝覆盖已有文件；不会自动安装凭证到 SmartGit 配置目录。服务器决定申请资格和截止日期；本工程不包含签发私钥。

申请成功后仅表示凭证已保存并验证，尚未在 SmartGit 中启用；后续需按 SmartGit 的授权流程操作。上述配置路径是现有文件的验证示例，脚本不会查找或创建 SmartGit 的配置目录。请勿提交凭证或专用 `machine-id` 文件到版本库。

实现限定于观察到的 Linux / SmartGit 26.1 / Format=3 evaluation 格式，内置该版本的验签公钥。未复现虚拟机分类（`AdditionalData` 为空）、`evaluatePing` 上报或应用后续宽限期及 UI 状态逻辑。

成功时输出 JSON，包含产品、主版本、有效截止日、签署时间、过期状态和签名/绑定检查结果；申请成功还包含 `saved_to`。输出不包含 EvaluationId、机器摘要或签名内容。有效期按本地时区计算，截止日当天的失效边界为本地午夜后 86,340 秒（23:59:00）。

evaluation 命令退出码：`0` 为验证通过且未过期，`2` 为离线验证通过但已过期，`1` 为请求、验证或文件操作失败；申请返回过期凭证时不会保存，返回 `1`。启动器管理命令成功返回 `0`，操作失败返回 `1`。两套 CLI 的参数解析错误均由 argparse 返回 `2`。

## 常见问题

- 提示 `Install bubblewrap (bwrap) first`：先通过系统包管理器安装 Bubblewrap，再运行 `install`。
- 提示 `Expected SmartGit installation under /usr/share/smartgit`：检查上述应用脚本和系统桌面入口是否均存在。
- Bubblewrap 报权限或命名空间错误：检查主机或容器的命名空间策略；安装探测失败时不会写入新的安装配置。
- `check` 提示找不到 `launch`：先运行 `install`，并确认使用相同的用户和 XDG 路径。
- evaluation 提示机器绑定不匹配：确保申请、验证和 SmartGit 启动使用相同的系统 ID 或专用 ID 环境。
- 申请提示输出已存在：改用尚不存在的文件名；脚本不会覆盖现有文件或符号链接。官方服务拒绝申请时，错误输出会包含 HTTP 状态和可解析的 `errorCode`。

## 开发与验证

```bash
python3 -m unittest discover -v
python3 smartgit_private_id.py --help
python3 smartgit_private_id.py install --help
python3 smartgit_evaluation.py --help
python3 smartgit_evaluation.py request --help
python3 smartgit_evaluation.py verify --help
```

测试使用临时目录和模拟子进程，不改动实际用户配置，不联网，也不启动 SmartGit。真实主机上的映射检查需要先由用户安装启动器，再运行 `check`；官方申请属于独立的联网操作。

## 可选 Bun 命令

无需 `bun install`；如已安装 Bun，可以继续使用：

```bash
bun run smartgit:privacy -- install
bun run smartgit:evaluation -- verify "$HOME/.config/smartgit/26.1/evaluation"
bun run test
```

Python 测试的 Bun 入口为 `bun run test`，或直接运行 `python3 -m unittest discover -v`。测试使用临时目录和模拟命名空间调用，不改动实际用户配置，也不联网。
