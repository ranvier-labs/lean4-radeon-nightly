"""Run a command while another process holds eight idle compute queues."""
import ctypes as C
import subprocess
import sys

def main(command):
    hip = C.CDLL("libamdhip64.so")
    def check(status):
        if status:
            raise RuntimeError(f"HIP call failed with status {status}")

    check(hip.hipSetDevice(0))
    streams = []
    try:
        mask = C.c_uint(3)
        for _ in range(8):
            stream = C.c_void_p()
            check(hip.hipExtStreamCreateWithCUMask(C.byref(stream), 1, C.byref(mask)))
            streams.append(stream)
        return subprocess.run(command).returncode
    finally:
        for stream in reversed(streams):
            check(hip.hipStreamDestroy(stream))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: with-extra-queues.py COMMAND [ARG ...]")
    raise SystemExit(main(sys.argv[1:]))
