# CPU Gate Evidence

This file records metadata-only CPU gate evidence for the system-audio MVP.
It must not include raw audio, transcript content, meeting titles, participant
names, or secrets.

Required acceptance gates:

- `idle`, `stop`, and `quit`: `coreaudiod < 5%` and combined app/helper `< 5%`
  after the settle window.
- `activeRecording`: no sustained `coreaudiod > 10%`.
- `activeRecording`: no sustained combined app/helper `> 25%`.
- `sustained`: at least three consecutive samples above threshold.

## 2026-06-08T17:11:50Z idle

- Command: `./apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`
- Note: Fast validation run only. It does not replace the later settled
  idle/stop/quit checks or active recording/manual release CPU evidence.

```text
2026-06-08T17:11:48Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:11:49Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:11:50Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T17:12:57Z idle

- Command: `./apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:12:55Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:12:56Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:12:57Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```
