"""
Windows Job Object 封装
- 创建带 KILL_ON_JOB_CLOSE 的 Job Object
- 将进程分配到 Job Object
- 关闭句柄时自动终止整个进程树
"""
import ctypes
import ctypes.wintypes as wintypes
import sys

if sys.platform != "win32":
    raise RuntimeError("Job Object 仅支持 Windows 平台")

kernel32 = ctypes.windll.kernel32

# 常量
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JobObjectExtendedLimitInformation = 9
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001
CREATE_NO_WINDOW = 0x08000000


# 结构体
class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def create_job_object() -> int:
    """
    创建一个 Job Object，配置 KILL_ON_JOB_CLOSE。
    当句柄关闭时，关联的所有进程（含子进程）自动终止。
    返回句柄（整数）。
    """
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError()

    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

    result = kernel32.SetInformationJobObject(
        handle,
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not result:
        kernel32.CloseHandle(handle)
        raise ctypes.WinError()

    return handle


def assign_process_to_job(job_handle: int, pid: int) -> bool:
    """将进程分配到 Job Object"""
    proc_handle = kernel32.OpenProcess(
        PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid
    )
    if not proc_handle:
        return False

    result = kernel32.AssignProcessToJobObject(job_handle, proc_handle)
    kernel32.CloseHandle(proc_handle)
    return bool(result)


def close_job_object(job_handle: int):
    """关闭 Job Object 句柄，终止关联的所有进程树成员"""
    if job_handle:
        kernel32.CloseHandle(job_handle)