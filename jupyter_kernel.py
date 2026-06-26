import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import time
import signal
import psutil
import socket

from jupyter_client.manager import KernelManager


class ExecutionResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    images: Optional[List[str]] = None


def get_host_ip():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return "0.0.0.0"


class JupyterKernel:
    def __init__(self):
        self.km = None
        self.kc = None
        self.connection_file = None
        self._start_kernel()

    def _start_kernel(self):
        try:
            if self.km:
                self.shutdown()

            self.km = KernelManager(ip=get_host_ip())
            self.km.start_kernel()
            self.connection_file = self.km.connection_file
            self.kc = self.km.client()
            self.kc.start_channels()

            # 等待 kernel 完全准备好
            timeout = 30
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    raise Exception("Timeout waiting for kernel to start")
                try:
                    self.kc.wait_for_ready(timeout=timeout)
                    break
                except Exception as e:
                    if "Timeout" not in str(e):
                        raise
                    continue

            # 初始化必要的包和配置
            init_code = """
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from IPython.display import display
%matplotlib inline

# 设置 matplotlib 中文字体支持
plt.style.use('default')
plt.rcParams['figure.figsize'] = [8, 6]
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 100
plt.rcParams['font.size'] = 10
plt.rcParams['axes.grid'] = True
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'
plt.rcParams['savefig.edgecolor'] = 'none'

# 配置中文字体
# 强制重新初始化字体管理器以识别新安装的字体
fm.fontManager.__init__()

# 查找可用的 CJK 字体
cjk_fonts = [f.name for f in fm.fontManager.ttflist if 'CJK' in f.name]
if cjk_fonts:
    # 优先使用简体中文字体，如果没有则使用日文字体（也支持中文）
    preferred_fonts = ['Noto Sans CJK SC', 'Noto Sans CJK TC', 'Noto Sans CJK JP']
    selected_font = None
    for font in preferred_fonts:
        if font in cjk_fonts:
            selected_font = font
            break

    if selected_font:
        plt.rcParams['font.family'] = selected_font
    else:
        # 使用找到的第一个 CJK 字体
        plt.rcParams['font.family'] = list(set(cjk_fonts))[0]
else:
    # 回退到默认配置
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Noto Sans CJK TC', 'DejaVu Sans']

plt.rcParams['axes.unicode_minus'] = False
"""
            self.execute(init_code)
        except Exception as e:
            print(f"Kernel initialization error: {str(e)}")
            self.shutdown()
            raise

    def _ensure_kernel_alive(self):
        """确保 kernel 是活跃的，如果不是则重启"""
        try:
            if not self.kc or not self.km:
                raise Exception("Kernel not initialized")

            # 检查 kernel 是否还在运行
            if not self.km.is_alive():
                raise Exception("Kernel is not alive")

            # 检查 kernel 是否响应
            try:
                self.kc.kernel_info()
            except Exception:
                raise Exception("Kernel is not responding")

        except Exception as e:
            print(f"Kernel check failed: {str(e)}")
            self._start_kernel()

    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        try:
            # 确保 kernel 是活跃的
            self._ensure_kernel_alive()

            # 执行用户代码
            if not self.kc:
                raise Exception("Kernel not initialized")

            msg_id = self.kc.execute(code)

            # 等待执行结果
            output = []
            error = None
            images = []
            start_time = time.time()
            removed_prefix = False

            while True:
                try:
                    if time.time() - start_time > timeout:
                        return ExecutionResult(
                            success=False,
                            output="",
                            error=f"Executing code timed out, timeout: {timeout} seconds",
                            images=[],
                        )

                    msg = self.kc.get_iopub_msg(timeout=timeout + 1)
                    msg_type = msg["header"]["msg_type"]

                    if msg_type == "stream":
                        # 直接添加 stream 输出，不需要清理
                        output.append(msg["content"]["text"])
                    elif msg_type == "error":
                        error = "\n".join(msg["content"]["traceback"])
                    elif msg_type == "execute_result":
                        if isinstance(msg["content"]["data"], dict):
                            if "text/plain" in msg["content"]["data"]:
                                text = msg["content"]["data"]["text/plain"]
                                # # 去除第一个行号字符
                                # if not removed_prefix:
                                #     text = text[1:]
                                #     removed_prefix = True
                                output.append(text)
                            if "image/png" in msg["content"]["data"]:
                                images.append(msg["content"]["data"]["image/png"])
                    elif msg_type == "display_data":
                        if isinstance(msg["content"]["data"], dict):
                            if "image/png" in msg["content"]["data"]:
                                images.append(msg["content"]["data"]["image/png"])
                            elif "text/plain" in msg["content"]["data"]:
                                text = msg["content"]["data"]["text/plain"]
                                output.append(text)

                    if (
                        msg["parent_header"]["msg_id"] == msg_id
                        and msg_type == "status"
                        and msg["content"]["execution_state"] == "idle"
                    ):
                        break
                except Exception as e:
                    if str(e) == "Timeout waiting for message":
                        continue
                    raise e

            # 合并输出，保持换行符
            final_output = "".join(output).strip()
            return ExecutionResult(
                success=error is None,  # 如果有错误，则 success 为 False
                output=final_output,
                error=error,
                images=images,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Execution error: {e.__class__.__name__} {str(e)}")
            # 如果执行出错，尝试重启 kernel
            try:
                self._start_kernel()
            except Exception as restart_error:
                print(f"Failed to restart kernel: {str(restart_error)}")
            raw_error = f"{e.__class__.__name__}: {str(e)}"
            if "empty" in raw_error.lower():
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Executing code timed out, timeout: {timeout} seconds",
                    images=[],
                )
            else:
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"{e.__class__.__name__}: {str(e)}",
                    images=[],
                )

    def reset_kernel(self) -> Dict[str, Any]:
        """重置 kernel"""
        try:
            print("Resetting kernel...")
            old_connection_file = self.connection_file
            self.shutdown()
            self._start_kernel()
            return {
                "success": True,
                "message": "Kernel reset successfully",
                "old_connection_file": old_connection_file,
                "new_connection_file": self.connection_file,
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to reset kernel: {str(e)}"}

    def interrupt_kernel(self) -> Dict[str, Any]:
        """中断 kernel 执行"""
        try:
            if not self.km:
                return {"success": False, "message": "Kernel not initialized"}

            # 获取 kernel 进程 ID
            kernel_id = self._get_kernel_pid()

            if kernel_id:
                # 发送 SIGINT 信号中断 kernel
                try:
                    process = psutil.Process(kernel_id)
                    process.send_signal(signal.SIGINT)
                    print(f"Sent SIGINT to kernel process {kernel_id}")
                except psutil.NoSuchProcess:
                    print(f"Kernel process {kernel_id} not found")
                except Exception as e:
                    print(f"Error sending signal to kernel process: {str(e)}")

            # 也可以通过 jupyter client 发送中断
            try:
                if self.kc and hasattr(self.kc, "interrupt"):
                    self.kc.interrupt()  # type: ignore
            except (AttributeError, Exception):
                # 某些版本的 client 可能没有 interrupt 方法或者方法调用失败
                pass

            return {
                "success": True,
                "message": "Kernel interrupted successfully",
                "kernel_pid": kernel_id,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to interrupt kernel: {str(e)}",
            }

    def get_connection_info(self) -> Dict[str, Any]:
        """获取 kernel 连接信息"""
        try:
            if not self.km or not self.connection_file:
                return {
                    "success": False,
                    "message": "Kernel not initialized",
                    "kernel_alive": False,
                }

            # 读取 connection file 的内容
            with open(self.connection_file, "r") as f:
                connection_info = json.load(f)

            return {
                "success": True,
                "connection_file": self.connection_file,
                "connection_info": connection_info,
                "kernel_alive": self.km.is_alive(),
                "kernel_pid": self._get_kernel_pid(),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get connection info: {str(e)}",
                "kernel_alive": False,
            }

    def get_kernel_status(self) -> Dict[str, Any]:
        """获取 kernel 状态"""
        try:
            if not self.km:
                return {
                    "success": False,
                    "message": "Kernel manager not initialized",
                    "kernel_alive": False,
                    "client_connected": False,
                }

            kernel_alive = self.km.is_alive()
            kernel_pid = self._get_kernel_pid()
            connection_file = self.connection_file

            # 检查 client 是否连接
            client_connected = False
            if self.kc:
                try:
                    self.kc.kernel_info()
                    client_connected = True
                except Exception:
                    client_connected = False

            return {
                "success": True,
                "kernel_alive": kernel_alive,
                "kernel_pid": kernel_pid,
                "connection_file": connection_file,
                "client_connected": client_connected,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get kernel status: {str(e)}",
                "kernel_alive": False,
                "client_connected": False,
            }

    def shutdown(self):
        """关闭 kernel"""
        try:
            if self.kc:
                self.kc.stop_channels()
                self.kc = None
            if self.km:
                self.km.shutdown_kernel(now=True)
                self.km = None
            self.connection_file = None
        except Exception as e:
            print(f"Shutdown error: {str(e)}")

    def _get_kernel_pid(self) -> Optional[int]:
        """获取 kernel 进程 ID"""
        try:
            if not self.km:
                return None
            return self.km.provisioner.pid if hasattr(self.km, "provisioner") else None
        except Exception:
            return None

    def debug_kernel_manager(self) -> Dict[str, Any]:
        """调试 kernel 管理器状态"""
        try:
            debug_info = {
                "has_km": self.km is not None,
                "has_kc": self.kc is not None,
                "connection_file": self.connection_file,
            }

            if self.km:
                debug_info["kernel_alive"] = self.km.is_alive()
                debug_info["kernel_pid"] = self._get_kernel_pid()
                debug_info["has_provisioner"] = hasattr(self.km, "provisioner")
                debug_info["km_attrs"] = [
                    attr for attr in dir(self.km) if not attr.startswith("_")
                ]

            if self.kc:
                debug_info["kc_attrs"] = [
                    attr for attr in dir(self.kc) if not attr.startswith("_")
                ]

            return debug_info
        except Exception as e:
            return {"error": str(e)}

    def restart_kernel(self) -> Dict[str, Any]:
        """重启 kernel（保留用于向后兼容）"""
        return self.reset_kernel()
