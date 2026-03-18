# 如何查看 ParaViewWeb (pvweb) 的终端/日志与 Python 报错

真实模式仿真启动后，pvweb 在 WSL 内以后台进程方式运行，**所有标准输出和 Python traceback 都会写入日志文件**，便于排查 3D 流场连接失败或 RPC 报错（如 -32001 Exception raised）。

## 1. 日志文件位置（推荐）

后端启动 pvweb 时会自动把输出写入：

```
heat_exchanger_ai/logs/pvweb_<仿真ID>.log
```

- **仿真ID**：当前运行中的仿真任务 ID（例如 WebSocket 或接口返回的 `simulation_id`）。
- 项目根路径示例：`d:\openfoam闭环生态\heat_exchanger_ai\logs\pvweb_xxx.log`。

**查看方式：**

- 用记事本、VS Code 或任意编辑器打开该文件即可看到 pvweb 的完整输出和 Python 报错（含 traceback）。
- 仿真运行过程中可随时打开并**刷新**该文件，新输出会持续追加。
- 若 3D 视图报「Exception raised」或 -32001，打开对应 `pvweb_<仿真ID>.log`，拉到底部查看最新异常堆栈。

## 2. 在 WSL 终端里手动运行 pvweb（用于调试）

若需要**在 WSL 里直接看到终端输出**（不经过日志文件），可以手动在 WSL 中启动 pvweb，这样所有 print 和 traceback 会打在当前终端。

### 2.1 若出现 `pvpython: command not found`

说明当前 WSL 里**没有安装带 Python 的 ParaView**，或可执行文件不在 `PATH` 里。任选其一即可：

**方式 A：用 apt 安装 ParaView（推荐，简单）**

```bash
sudo apt update
sudo apt install paraview python3-paraview
```

安装后先确认是否有 `pvpython`：

```bash
which pvpython
# 若没有，再试（部分发行版把可执行文件放在别处）：
dpkg -L python3-paraview | grep -E 'bin|pvpython'
```

若仍没有 `pvpython`，可用**方式 B** 用系统 Python 跑（前提是已装 `paraview` 和 `paraview-web`）：

```bash
python3 -c "import paraview.web.serve" && echo "OK"
```

若输出 `OK`，则可用下面「方式 B」里的命令用 `python3` 代替 `pvpython` 运行本项目的 `pvweb_server.py`（需能 `import paraview.web` 和 `wslink`）。

**方式 B：用系统 Python 代替 pvpython**

若已用 pip 或 apt 装好了 `paraview` / `paraview-web` 和 `wslink`，可直接用：

```bash
python3 backend/services/pvweb_server.py \
  --data /path/to/your/case.foam \
  --host 0.0.0.0 \
  --port 9000
```

（同样需要能 `import paraview.web` 和 `wslink`，否则需先 `pip install wslink` 等。）

**方式 C：从 Kitware 下载 ParaView 并用自己的 pvpython**

1. 在 [ParaView 官网](https://www.paraview.org/download/) 下载 Linux 版（例如 `.tar.gz`）。
2. 解压到如 `/opt/paraview`，将 **`/opt/paraview/bin`** 加入 `PATH`，或直接用绝对路径：
   ```bash
   /opt/paraview/bin/pvpython backend/services/pvweb_server.py --data ... --host 0.0.0.0 --port 9000
   ```

---

### 2.2 有 pvpython 时的手动运行步骤

1. 打开 **WSL 终端**（例如 `wsl -d Ubuntu-24.04` 或你的发行版）。
2. 进入项目并加载 OpenFOAM 环境（若需要）：
   ```bash
   source /opt/openfoam11/etc/bashrc   # 路径以你实际 openfoam_path 为准
   cd /mnt/d/openfoam闭环生态/heat_exchanger_ai   # 项目在 WSL 下的路径
   ```
3. 用 **pvpython**（或上面方式 B 的 **python3**）运行 pvweb_server（把 `case.foam` 路径和端口换成你当前仿真的）：
   ```bash
   pvpython backend/services/pvweb_server.py \
     --data /path/to/your/case.foam \
     --host 0.0.0.0 \
     --port 9000
   ```
4. 终端里会**实时**输出所有日志和 Python 报错；按 `Ctrl+C` 可停止。

**注意**：手动运行时，同一端口不要与后端自动启动的 pvweb 冲突（要么先停止该仿真的 pvweb，要么换一个端口）。

## 3. 通过 API 拿到当前仿真的日志路径

若前端或脚本需要知道「当前仿真对应的 pvweb 日志文件路径」，可调用：

```
GET /api/simulation/<simulation_id>/paraview-web
```

响应里会包含 `log_path` 字段（当 pvweb 已启动时），即该仿真的 pvweb 日志文件路径，便于自动打开或展示给用户。

## 4. 常见报错在日志中的样子

- **pvpython: command not found**（在 WSL 里手动跑时）：见上文 **2.1**，先安装 ParaView（如 `sudo apt install paraview python3-paraview`）或改用 `python3` / 官方安装包里的 `pvpython`。
- **ImportError / ModuleNotFoundError**：WSL 里未装全 `paraview`、`wslink` 或 `paraview.web`，需在 WSL 内用 pip 或系统包安装。
- **FileNotFoundError / 找不到 case.foam**：`--data` 指向的路径在 WSL 下不存在或拼写错误，检查仿真 case 目录和 `case.foam` 是否已生成。
- **Exception raised (-32001)**：RPC 调用时服务端抛异常，日志里会有完整 Python traceback，根据最后几行定位到具体代码和原因。

总结：**优先看 `heat_exchanger_ai/logs/pvweb_<仿真ID>.log`**；需要边改边看输出时，再用 WSL 终端手动运行 `pvpython backend/services/pvweb_server.py ...`。
