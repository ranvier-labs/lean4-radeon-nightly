## Cooperative kernels on gfx1151

On Linux `7.2.7+rex-amd64` with the stock driver and ROCm `10.0.0-4`, a
process can stall when loading a second GPU code object after a cooperative
kernel completes. This was reproduced on `gfx1151` after synchronizing the
launch stream.

To run a workload under the queue configuration used for validation, download
[with-extra-queues.py](https://github.com/ranvier-labs/lean4-radeon-nightly/blob/main/scripts/with-extra-queues.py)
and run it on the GPU host:

```sh
python3 with-extra-queues.py ./my-hip-program
```

The helper loads `libamdhip64.so` and holds eight idle HIP streams on device
zero with CU mask `0x3` while the command runs. It changes GPU scheduling
for the duration of that command.
