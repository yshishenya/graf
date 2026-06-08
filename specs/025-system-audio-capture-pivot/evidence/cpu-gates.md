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

## 2026-06-08T17:27:45Z idle

- Command: `./apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:27:42Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:27:44Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:27:45Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T17:36:48Z idle

- Command: `./apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:36:46Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:36:47Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:36:48Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```

## 2026-06-08T17:38:29Z idle

- Command: `./apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:38:26Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T17:38:27Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T17:38:29Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```

## 2026-06-08T17:40:20Z idle

- Command: `./apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=4.20 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:40:17Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=4.20 helperCpuPercent=0.00 appHelperCpuPercent=4.20 halProbeObserved=false
2026-06-08T17:40:19Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T17:40:20Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```
