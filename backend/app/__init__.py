# Backend App Package
import platform
if hasattr(platform, "_wmi_query"):
    platform._wmi_query = lambda table, *args: ("10.0.22631", 1, "Multiprocessor Free", 0, 0)
