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

## 2026-06-08T17:54:59Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=1.90 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:54:57Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=1.90 helperCpuPercent=0.00 appHelperCpuPercent=1.90 halProbeObserved=false
2026-06-08T17:54:58Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T17:54:59Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T17:56:56Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=1.90 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:56:54Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=1.90 helperCpuPercent=0.00 appHelperCpuPercent=1.90 halProbeObserved=false
2026-06-08T17:56:55Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:56:56Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T17:58:21Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=failed failureReason=cpuGateFailed sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=30.30 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=true`

```text
2026-06-08T17:58:18Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=4.60 helperCpuPercent=0.00 appHelperCpuPercent=4.60 halProbeObserved=false
2026-06-08T17:58:19Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=30.30 helperCpuPercent=0.00 appHelperCpuPercent=30.30 halProbeObserved=false
2026-06-08T17:58:21Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T17:59:02Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T17:58:57Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:58:59Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T17:59:02Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:04:27Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=failed failureReason=cpuGateFailed sampleCount=3 maxCoreaudiodCpuPercent=5.70 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=true sustainedAppHelperExceeded=false`

```text
2026-06-08T18:04:23Z phase=idle sample=1 coreaudiodCpuPercent=5.70 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:04:25Z phase=idle sample=2 coreaudiodCpuPercent=5.40 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T18:04:27Z phase=idle sample=3 coreaudiodCpuPercent=5.30 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:10:43Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:10:41Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:10:42Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:10:43Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:11:15Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:11:13Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:14Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:15Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:11:17Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:11:15Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:16Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:17Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:11:42Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:11:40Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:41Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:42Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:11:42Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:11:40Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:41Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:11:42Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:12:50Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:12:46Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T18:12:48Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:12:50Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```

## 2026-06-08T18:13:27Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:13:22Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:13:24Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:13:27Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:30:48Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:30:44Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:30:46Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:30:48Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:32:00Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:31:55Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T18:31:57Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:32:00Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```

## 2026-06-08T18:34:46Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:34:42Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T18:34:44Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:34:46Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:36:39Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:36:35Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:36:37Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:36:39Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T18:47:31Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:47:27Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T18:47:29Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:47:31Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```

## 2026-06-08T18:54:41Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T18:54:37Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:54:39Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T18:54:41Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:10:50Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:10:46Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:10:48Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T19:10:50Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:11:31Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:11:27Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:11:29Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:11:31Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:19:09Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:19:05Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T19:19:07Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:19:09Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:20:10Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:20:06Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:20:08Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:20:10Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:29:12Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:29:07Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T19:29:10Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T19:29:12Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```

## 2026-06-08T19:29:58Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:29:54Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:29:56Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:29:58Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:45:19Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:45:15Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:45:17Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:45:19Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:45:40Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:45:36Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T19:45:38Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
2026-06-08T19:45:40Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 halProbeObserved=false
```

## 2026-06-08T19:48:14Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:48:09Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:48:12Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:48:14Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:48:45Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:48:41Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:48:43Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:48:45Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:49:16Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:49:11Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:49:13Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
2026-06-08T19:49:16Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 halProbeObserved=false
```

## 2026-06-08T19:50:17Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=failed failureReason=appStillRunning sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:50:15Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:16Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:17Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T19:50:38Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:50:36Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:37Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:38Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T19:50:53Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:50:51Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:52Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:53Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T19:50:56Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T19:50:53Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:54Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T19:50:56Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:10:34Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:10:30Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:10:32Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:10:34Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:10:40Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:10:38Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:10:39Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:10:40Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:15:01Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:14:56Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:14:59Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:15:01Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:15:06Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:15:04Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:15:05Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:15:06Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:19:38Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:19:34Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:19:36Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:19:38Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:19:45Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:19:42Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:19:43Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:19:45Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:24:26Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:24:22Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:24:24Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:24:26Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:24:33Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:24:31Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:24:32Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:24:33Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:28:19Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:28:14Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:28:16Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:28:19Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:28:25Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:28:23Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:28:24Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:28:25Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:35:21Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:35:16Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:35:19Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:35:21Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:35:27Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:35:25Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:35:26Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:35:27Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:42:35Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:42:31Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:42:33Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:42:35Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:43:16Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:43:13Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:43:15Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:43:16Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:46:58Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:46:54Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:46:56Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:46:58Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:47:05Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:47:02Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:47:04Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:47:05Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:49:08Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:49:04Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:49:06Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:49:08Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:49:15Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:49:13Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:49:14Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:49:15Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:53:46Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:53:42Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:53:44Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:53:46Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:53:53Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:53:51Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:53:52Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:53:53Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:56:18Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:56:13Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:56:15Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:56:18Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T20:56:24Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T20:56:22Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:56:23Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T20:56:24Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:01:35Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:01:31Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:01:33Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:01:35Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:01:42Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:01:40Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:01:41Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:01:42Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:07:20Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:07:16Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:07:18Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:07:20Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:07:27Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:07:25Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:07:26Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:07:27Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:12:05Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:12:01Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:12:03Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:12:05Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:12:11Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:12:09Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:12:10Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:12:11Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:21:05Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:21:01Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:21:03Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:21:05Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:23:51Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:23:47Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:23:49Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:23:51Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:24:09Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:24:07Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:24:08Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:24:09Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:31:10Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:31:06Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:31:08Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:31:10Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:31:26Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:31:24Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:31:25Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:31:26Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:39:29Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:39:25Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:39:27Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:39:29Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:39:47Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:39:45Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:39:46Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:39:47Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:45:37Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:45:32Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:45:34Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:45:37Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:45:56Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:45:54Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:45:55Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:45:56Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:51:20Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:51:15Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:51:18Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:51:20Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:51:38Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:51:36Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:51:37Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:51:38Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:56:25Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:56:21Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:56:23Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:56:25Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T21:56:42Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T21:56:39Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:56:41Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T21:56:42Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:02:35Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:02:31Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:02:33Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:02:35Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:02:52Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:02:50Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:02:51Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:02:52Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:10:24Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:10:20Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:10:22Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:10:24Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:10:40Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:10:38Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:10:39Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:10:40Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:32:39Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:32:34Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:32:36Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:32:39Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:32:52Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:32:49Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:32:50Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:32:52Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:43:34Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:43:30Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:43:32Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:43:34Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:43:47Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:43:45Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:43:46Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:43:47Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:49:06Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:49:01Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:49:03Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:49:06Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:49:19Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:49:16Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:49:17Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:49:19Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:54:00Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:53:56Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:53:58Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:54:00Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:54:14Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:54:11Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:54:13Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:54:14Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:59:36Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:59:31Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:59:34Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:59:36Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T22:59:49Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T22:59:47Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:59:48Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T22:59:49Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:06:26Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:06:22Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:06:24Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:06:26Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:07:21Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:07:17Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:07:19Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:07:21Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:17:03Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:16:58Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:17:01Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:17:03Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:17:37Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:17:33Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:17:35Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:17:37Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:23:45Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:23:40Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:23:43Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:23:45Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:24:24Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:24:20Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:24:22Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:24:24Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:29:43Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:29:39Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:29:41Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:29:43Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:30:21Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:30:16Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:30:19Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:30:21Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:35:57Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.50 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:35:53Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:35:55Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:35:57Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.50 helperCpuPercent=0.00 appHelperCpuPercent=0.50 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:36:41Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:36:36Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:36:39Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:36:41Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:49:03Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:48:59Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:49:01Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:49:03Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:50:30Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=failed failureReason=appStillRunning sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`
- Operator note: this was an invalid quit-gate attempt because the sampler was
  started in parallel with the quit command, so sample 1 observed the app before
  termination completed. The immediate follow-up quit gate below was run after
  the app process had exited and passed with `maxAppProcessCount=0`.

```text
2026-06-08T23:50:28Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:50:29Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:50:30Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:50:44Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:50:42Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:50:43Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:50:44Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```


## 2026-06-08T23:52:44Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:52:40Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:52:42Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:52:44Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-08T23:53:22Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-08T23:53:20Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:53:21Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-08T23:53:22Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:16:27Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:16:23Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:16:25Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:16:27Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:16:43Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:16:41Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:16:42Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:16:43Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:22:03Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:21:59Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:22:01Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:22:03Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:22:17Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:22:15Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:22:16Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:22:17Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:28:18Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.30 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:28:14Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:28:16Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:28:18Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.30 helperCpuPercent=0.00 appHelperCpuPercent=0.30 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:28:36Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:28:34Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:28:35Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:28:36Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:34:12Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:34:08Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:34:10Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:34:12Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:34:29Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:34:27Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:34:28Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:34:29Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:46:50Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:46:48Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:46:49Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:46:50Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:48:26Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:48:24Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:48:25Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:48:26Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:50:10Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.40 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:50:07Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:50:08Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:50:10Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.40 helperCpuPercent=0.00 appHelperCpuPercent=0.40 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:50:15Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:50:13Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:50:14Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:50:15Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:57:25Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:57:23Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:57:24Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:57:25Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T00:57:31Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `1`, settle seconds: `0`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T00:57:29Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:57:30Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T00:57:31Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T01:21:42Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=1.70 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T01:21:38Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T01:21:40Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=1.70 helperCpuPercent=0.00 appHelperCpuPercent=1.70 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T01:21:42Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T01:21:55Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `2`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T01:21:51Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T01:21:53Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T01:21:55Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T02:06:43Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T02:06:39Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:06:41Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:06:43Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T02:15:54Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T02:15:50Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:15:52Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:15:54Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T02:23:05Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T02:23:01Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:23:03Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:23:05Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T02:30:47Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T02:30:42Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:30:45Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:30:47Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T02:37:07Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T02:37:03Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:37:05Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:37:07Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T02:46:07Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T02:46:02Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:46:04Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:46:07Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T02:52:48Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T02:52:44Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:52:46Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T02:52:48Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:00:53Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:00:49Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:00:51Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:00:53Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:24:18Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `5`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=5 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:24:09Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:12Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:14Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:16Z phase=idle sample=4 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:18Z phase=idle sample=5 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:24:45Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `5`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=5 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:24:37Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:39Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:41Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:43Z phase=quit sample=4 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:24:45Z phase=quit sample=5 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:28:38Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `5`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=5 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:28:30Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:28:32Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:28:34Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:28:36Z phase=idle sample=4 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:28:38Z phase=idle sample=5 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:29:05Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `5`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=5 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:28:56Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:28:58Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:29:00Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:29:02Z phase=quit sample=4 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:29:05Z phase=quit sample=5 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:34:45Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `5`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=5 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:34:36Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:34:38Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:34:41Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:34:43Z phase=quit sample=4 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:34:45Z phase=quit sample=5 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:40:20Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `5`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=passed failureReason=none sampleCount=5 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:40:11Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:13Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:15Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:17Z phase=idle sample=4 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:20Z phase=idle sample=5 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:40:47Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `5`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=5 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:40:39Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:41Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:43Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:45Z phase=quit sample=4 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:40:47Z phase=quit sample=5 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:45:08Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `1`, settle seconds: `2`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:45:05Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:45:07Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:45:08Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:49:25Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `1`, settle seconds: `2`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:49:23Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:49:24Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:49:25Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T03:53:42Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `1`, settle seconds: `2`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T03:53:39Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:53:41Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T03:53:42Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:01:04Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:01:00Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:01:02Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:01:04Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:06:26Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.20 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:06:22Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.20 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:06:24Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.20 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:06:26Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.20 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:11:07Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.28 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:11:02Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.28 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:11:04Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.28 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:11:07Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.28 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:16:22Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.30 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:16:18Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.30 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:16:20Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:16:22Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:22:06Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.36 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:22:02Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:22:04Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:22:06Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:27:18Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.38 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:27:14Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:27:16Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:27:18Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:30:10Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.33 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:30:06Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.33 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:30:08Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.33 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:30:10Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.33 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:34:35Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.38 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:34:31Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:34:33Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:34:35Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:39:07Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.39 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:39:03Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:39:05Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:39:07Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:43:46Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.39 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:43:42Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:43:44Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:43:46Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:47:46Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.39 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:47:41Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:47:44Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:47:46Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:52:03Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.41 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:51:59Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.41 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:52:01Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.41 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:52:03Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.41 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T04:56:18Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.42 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T04:56:14Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.41 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:56:16Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T04:56:18Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:00:59Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.38 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:00:55Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:00:57Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:00:59Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.38 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:04:41Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.42 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:04:37Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:04:39Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:04:41Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:08:43Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.42 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:08:39Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:08:41Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:08:43Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:14:04Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.42 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:14:00Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:14:02Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:14:04Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.42 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:18:02Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.78 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:17:58Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:18:00Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:18:02Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:18:12Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.78 maxAppHelperRssMB=93.11 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:18:07Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=93.11 helperRssMB=0.00 appHelperRssMB=93.11 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:18:09Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=93.06 helperRssMB=0.00 appHelperRssMB=93.06 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:18:12Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=93.06 helperRssMB=0.00 appHelperRssMB=93.06 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:18:21Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.80 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:18:17Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.80 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:18:19Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.80 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:18:21Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.75 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:21:57Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.78 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:21:53Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:21:55Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:21:57Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:22:07Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.78 maxAppHelperRssMB=93.11 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:22:03Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=93.11 helperRssMB=0.00 appHelperRssMB=93.11 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:22:05Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=93.06 helperRssMB=0.00 appHelperRssMB=93.06 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:22:07Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=93.06 helperRssMB=0.00 appHelperRssMB=93.06 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:22:17Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.80 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:22:12Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:22:14Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.78 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:22:17Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.80 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:28:47Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.55 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:28:43Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:28:45Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:28:47Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:28:57Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.55 maxAppHelperRssMB=93.44 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:28:52Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=93.44 helperRssMB=0.00 appHelperRssMB=93.44 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:28:54Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=93.42 helperRssMB=0.00 appHelperRssMB=93.42 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:28:57Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=93.42 helperRssMB=0.00 appHelperRssMB=93.42 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:29:06Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.55 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:29:02Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:29:04Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:29:06Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:33:07Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.53 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:33:03Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.53 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:33:05Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.53 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:33:07Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.53 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:33:17Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxCoreaudiodRssMB=57.55 maxAppHelperRssMB=93.05 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:33:13Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.53 appRssMB=93.05 helperRssMB=0.00 appHelperRssMB=93.05 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:33:15Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=57.55 appRssMB=93.05 helperRssMB=0.00 appHelperRssMB=93.05 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:33:17Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=93.05 helperRssMB=0.00 appHelperRssMB=93.05 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:33:27Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.50 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:33:22Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:33:25Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:33:27Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:43:28Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.52 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:43:23Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:43:25Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:43:28Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:43:37Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.52 maxAppHelperRssMB=93.58 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:43:33Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=93.58 helperRssMB=0.00 appHelperRssMB=93.58 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:43:35Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=93.53 helperRssMB=0.00 appHelperRssMB=93.53 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:43:37Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=93.53 helperRssMB=0.00 appHelperRssMB=93.53 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:43:47Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.52 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:43:43Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:43:45Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:43:47Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:47:10Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.30 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.91 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:47:05Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:47:07Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:47:10Z phase=baseline sample=3 coreaudiodCpuPercent=0.30 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.91 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:54:39Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.03 maxAppHelperRssMB=93.08 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:54:34Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.03 appRssMB=93.08 helperRssMB=0.00 appHelperRssMB=93.08 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:54:37Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.98 appRssMB=93.03 helperRssMB=0.00 appHelperRssMB=93.03 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:54:39Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.80 appRssMB=93.03 helperRssMB=0.00 appHelperRssMB=93.03 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T05:54:48Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=57.70 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T05:54:44Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.70 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:54:46Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.70 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T05:54:48Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=57.70 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:12:04Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=1.30 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.73 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:12:00Z phase=baseline sample=1 coreaudiodCpuPercent=1.30 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.73 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:12:02Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.73 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:12:04Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:12:14Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxCoreaudiodRssMB=58.34 maxAppHelperRssMB=93.16 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:12:09Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.34 appRssMB=93.16 helperRssMB=0.00 appHelperRssMB=93.16 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:12:11Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=58.34 appRssMB=93.11 helperRssMB=0.00 appHelperRssMB=93.11 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:12:14Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.34 appRssMB=93.11 helperRssMB=0.00 appHelperRssMB=93.11 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:12:23Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.34 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:12:19Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.34 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:12:21Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.34 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:12:23Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.34 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:34:44Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.36 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:34:40Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:34:42Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:34:44Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:34:54Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.38 maxAppHelperRssMB=93.09 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:34:50Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.38 appRssMB=93.09 helperRssMB=0.00 appHelperRssMB=93.09 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:34:52Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.38 appRssMB=93.05 helperRssMB=0.00 appHelperRssMB=93.05 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:34:54Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.38 appRssMB=93.05 helperRssMB=0.00 appHelperRssMB=93.05 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:35:04Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.36 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:34:59Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:35:01Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:35:04Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.36 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:47:55Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.08 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:47:51Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.08 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:47:53Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.08 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:47:55Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.08 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:48:05Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxCoreaudiodRssMB=58.08 maxAppHelperRssMB=97.94 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:48:01Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=58.08 appRssMB=97.94 helperRssMB=0.00 appHelperRssMB=97.94 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:48:03Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=58.08 appRssMB=97.83 helperRssMB=0.00 appHelperRssMB=97.83 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:48:05Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=58.08 appRssMB=97.83 helperRssMB=0.00 appHelperRssMB=97.83 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:48:15Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.03 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:48:11Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:48:13Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:48:15Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:56:42Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.19 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:56:37Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.19 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:56:39Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.19 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:56:42Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.19 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:56:51Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.20 maxCoreaudiodRssMB=56.19 maxAppHelperRssMB=97.92 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:56:47Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=56.19 appRssMB=97.92 helperRssMB=0.00 appHelperRssMB=97.92 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:56:49Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.20 helperCpuPercent=0.00 appHelperCpuPercent=0.20 coreaudiodRssMB=56.19 appRssMB=97.83 helperRssMB=0.00 appHelperRssMB=97.83 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:56:51Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=56.19 appRssMB=97.83 helperRssMB=0.00 appHelperRssMB=97.83 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T06:57:01Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.19 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T06:56:57Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.19 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:56:59Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.19 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T06:57:01Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.19 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:06:04Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.23 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:06:00Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:06:02Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:06:04Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:06:14Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.23 maxAppHelperRssMB=93.16 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:06:09Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=93.16 helperRssMB=0.00 appHelperRssMB=93.16 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:06:12Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=93.03 helperRssMB=0.00 appHelperRssMB=93.03 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:06:14Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=93.03 helperRssMB=0.00 appHelperRssMB=93.03 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:06:23Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.23 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:06:19Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:06:21Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:06:23Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:09:20Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.25 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:09:15Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:09:18Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:09:20Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:09:29Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.25 maxAppHelperRssMB=93.47 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:09:25Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=93.47 helperRssMB=0.00 appHelperRssMB=93.47 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:09:27Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=93.42 helperRssMB=0.00 appHelperRssMB=93.42 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:09:29Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=93.42 helperRssMB=0.00 appHelperRssMB=93.42 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:09:39Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.22 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:09:35Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.22 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:09:37Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.22 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:09:39Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.22 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:18:15Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.25 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:18:11Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:18:13Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:18:15Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:18:25Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.25 maxAppHelperRssMB=93.17 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:18:20Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=93.17 helperRssMB=0.00 appHelperRssMB=93.17 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:18:22Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=93.12 helperRssMB=0.00 appHelperRssMB=93.12 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:18:24Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=93.12 helperRssMB=0.00 appHelperRssMB=93.12 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:18:34Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.27 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:18:30Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.27 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:18:32Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:18:34Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:25:14Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.23 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:25:10Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:25:12Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:25:14Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:25:24Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.23 maxAppHelperRssMB=93.39 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:25:20Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=93.39 helperRssMB=0.00 appHelperRssMB=93.39 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:25:22Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=93.31 helperRssMB=0.00 appHelperRssMB=93.31 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:25:24Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=93.31 helperRssMB=0.00 appHelperRssMB=93.31 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:25:34Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=56.25 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:25:29Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.25 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:25:32Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:25:34Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=56.23 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:33:12Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=55.06 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:33:08Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=55.06 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:33:10Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=55.06 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:33:12Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=55.06 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:33:22Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.10 maxCoreaudiodRssMB=54.94 maxAppHelperRssMB=98.77 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:33:18Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=54.94 appRssMB=98.77 helperRssMB=0.00 appHelperRssMB=98.77 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:33:20Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.94 appRssMB=98.64 helperRssMB=0.00 appHelperRssMB=98.64 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:33:22Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.94 appRssMB=98.64 helperRssMB=0.00 appHelperRssMB=98.64 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:33:32Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=54.92 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:33:28Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.92 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:33:30Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.92 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:33:32Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.89 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:43:13Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=54.86 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:43:09Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.86 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:43:11Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.86 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:43:13Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.86 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:43:23Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.20 maxCoreaudiodRssMB=54.48 maxAppHelperRssMB=98.31 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:43:19Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=54.48 appRssMB=98.31 helperRssMB=0.00 appHelperRssMB=98.31 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:43:21Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.20 helperCpuPercent=0.00 appHelperCpuPercent=0.20 coreaudiodRssMB=54.48 appRssMB=98.27 helperRssMB=0.00 appHelperRssMB=98.27 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:43:23Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=54.48 appRssMB=98.27 helperRssMB=0.00 appHelperRssMB=98.27 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:43:33Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=42.97 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:43:28Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=42.97 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:43:30Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=42.95 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:43:33Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=42.95 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:51:33Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=67.41 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:51:28Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=67.41 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:51:31Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=67.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:51:33Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=67.39 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:51:43Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=2.20 maxCoreaudiodRssMB=64.50 maxAppHelperRssMB=96.69 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:51:39Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=2.20 helperCpuPercent=0.00 appHelperCpuPercent=2.20 coreaudiodRssMB=64.50 appRssMB=96.69 helperRssMB=0.00 appHelperRssMB=96.69 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:51:41Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.10 helperCpuPercent=0.00 appHelperCpuPercent=0.10 coreaudiodRssMB=64.50 appRssMB=96.69 helperRssMB=0.00 appHelperRssMB=96.69 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:51:43Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=96.69 helperRssMB=0.00 appHelperRssMB=96.69 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T07:51:53Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.50 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T07:51:48Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:51:51Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T07:51:53Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:01:30Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.53 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:01:26Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.53 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:01:28Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.53 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:01:30Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.53 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:01:40Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.50 maxAppHelperRssMB=93.81 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:01:36Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=93.81 helperRssMB=0.00 appHelperRssMB=93.81 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:01:38Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=93.77 helperRssMB=0.00 appHelperRssMB=93.77 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:01:40Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=93.77 helperRssMB=0.00 appHelperRssMB=93.77 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:01:50Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.50 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:01:45Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:01:47Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:01:50Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.50 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:07:52Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.52 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:07:48Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:07:50Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:07:52Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:08:02Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.52 maxAppHelperRssMB=93.34 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:07:57Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=93.34 helperRssMB=0.00 appHelperRssMB=93.34 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:07:59Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=93.28 helperRssMB=0.00 appHelperRssMB=93.28 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:08:02Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=93.28 helperRssMB=0.00 appHelperRssMB=93.28 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:08:11Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.52 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:08:07Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:08:09Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:08:11Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:14:23Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.55 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:14:19Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:14:21Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:14:23Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.55 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:14:33Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.55 maxAppHelperRssMB=93.58 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:14:28Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.55 appRssMB=93.58 helperRssMB=0.00 appHelperRssMB=93.58 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:14:31Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.55 appRssMB=93.53 helperRssMB=0.00 appHelperRssMB=93.53 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:14:33Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=93.53 helperRssMB=0.00 appHelperRssMB=93.53 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:14:42Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=64.52 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:14:38Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:14:40Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:14:42Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=64.52 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:19:54Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:19:50Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:19:52Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:19:54Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:20:04Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=93.45 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:20:00Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=93.45 helperRssMB=0.00 appHelperRssMB=93.45 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:20:02Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=93.41 helperRssMB=0.00 appHelperRssMB=93.41 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:20:04Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=93.41 helperRssMB=0.00 appHelperRssMB=93.41 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:20:14Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:20:09Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:20:11Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:20:14Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:25:38Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.64 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:25:33Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:25:35Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:25:38Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:25:47Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.64 maxAppHelperRssMB=93.41 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:25:43Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=93.41 helperRssMB=0.00 appHelperRssMB=93.41 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:25:45Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=93.36 helperRssMB=0.00 appHelperRssMB=93.36 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:25:47Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=93.36 helperRssMB=0.00 appHelperRssMB=93.36 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:25:57Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.64 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:25:53Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:25:55Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:25:57Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:31:25Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:31:20Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:31:22Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:31:25Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:31:34Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.69 maxAppHelperRssMB=93.75 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:31:30Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.69 appRssMB=93.75 helperRssMB=0.00 appHelperRssMB=93.75 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:31:32Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=93.70 helperRssMB=0.00 appHelperRssMB=93.70 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:31:34Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=93.70 helperRssMB=0.00 appHelperRssMB=93.70 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:31:44Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.66 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:31:39Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:31:42Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:31:44Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:37:53Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.66 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:37:48Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:37:51Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:37:53Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:38:02Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.66 maxAppHelperRssMB=93.36 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:37:58Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=93.36 helperRssMB=0.00 appHelperRssMB=93.36 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:38:00Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=93.31 helperRssMB=0.00 appHelperRssMB=93.31 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:38:02Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=93.31 helperRssMB=0.00 appHelperRssMB=93.31 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:38:12Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.66 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:38:08Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:38:10Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:38:12Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.66 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:41:09Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.64 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:41:04Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:41:06Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:41:09Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:41:18Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.64 maxAppHelperRssMB=93.64 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:41:14Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=93.64 helperRssMB=0.00 appHelperRssMB=93.64 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:41:16Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=93.64 helperRssMB=0.00 appHelperRssMB=93.64 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:41:18Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=93.64 helperRssMB=0.00 appHelperRssMB=93.64 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:41:28Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:41:24Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.64 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:41:26Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:41:28Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:47:01Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:46:57Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:46:59Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:47:01Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:47:11Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=93.44 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:47:06Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=93.44 helperRssMB=0.00 appHelperRssMB=93.44 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:47:09Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=93.39 helperRssMB=0.00 appHelperRssMB=93.39 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:47:11Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=93.39 helperRssMB=0.00 appHelperRssMB=93.39 appProcessCount=1 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:47:20Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=63.67 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false`

```text
2026-06-09T08:47:16Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:47:18Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
2026-06-09T08:47:20Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=63.67 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false
```

## 2026-06-09T08:53:42Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T08:53:38Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T08:53:40Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T08:53:42Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T08:53:52Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=93.36 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T08:53:47Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.36 helperRssMB=0.00 appHelperRssMB=93.36 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T08:53:49Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.23 helperRssMB=0.00 appHelperRssMB=93.23 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T08:53:52Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.23 helperRssMB=0.00 appHelperRssMB=93.23 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T08:54:01Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T08:53:57Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T08:53:59Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T08:54:01Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:01:03Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:00:59Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:01:01Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:01:03Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:01:13Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=93.70 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:01:09Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.70 helperRssMB=0.00 appHelperRssMB=93.70 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:01:11Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.70 helperRssMB=0.00 appHelperRssMB=93.70 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:01:13Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.70 helperRssMB=0.00 appHelperRssMB=93.70 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:01:23Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:01:18Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:01:20Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:01:23Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:07:13Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.03 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:07:09Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:07:11Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:07:13Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:07:23Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.03 maxAppHelperRssMB=93.41 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:07:19Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=93.41 helperRssMB=0.00 appHelperRssMB=93.41 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:07:21Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=93.34 helperRssMB=0.00 appHelperRssMB=93.34 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:07:23Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=93.34 helperRssMB=0.00 appHelperRssMB=93.34 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:07:33Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.05 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:07:28Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:07:30Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:07:33Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:12:47Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:12:43Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:12:45Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:12:47Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:12:57Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=93.66 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:12:53Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.66 helperRssMB=0.00 appHelperRssMB=93.66 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:12:55Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.66 helperRssMB=0.00 appHelperRssMB=93.66 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:12:57Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.66 helperRssMB=0.00 appHelperRssMB=93.66 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:13:07Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:13:02Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:13:05Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:13:07Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:20:57Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.03 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:20:53Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:20:55Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:20:57Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:21:07Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.03 maxAppHelperRssMB=93.45 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:21:02Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=93.45 helperRssMB=0.00 appHelperRssMB=93.45 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:21:04Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=93.41 helperRssMB=0.00 appHelperRssMB=93.41 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:21:07Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=93.41 helperRssMB=0.00 appHelperRssMB=93.41 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:21:16Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.03 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:21:12Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:21:14Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:21:16Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.03 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:26:47Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:26:42Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:26:44Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:26:47Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:26:56Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=93.17 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:26:52Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.17 helperRssMB=0.00 appHelperRssMB=93.17 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:26:54Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.12 helperRssMB=0.00 appHelperRssMB=93.12 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:26:56Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.12 helperRssMB=0.00 appHelperRssMB=93.12 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:27:06Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:27:02Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:27:04Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:27:06Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:30:41Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.00 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:30:37Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:30:39Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:30:41Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:30:51Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.00 maxAppHelperRssMB=93.11 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:30:46Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=93.11 helperRssMB=0.00 appHelperRssMB=93.11 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:30:48Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=93.06 helperRssMB=0.00 appHelperRssMB=93.06 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:30:51Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=93.06 helperRssMB=0.00 appHelperRssMB=93.06 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:31:00Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.00 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:30:56Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:30:58Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:31:00Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.00 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:36:57Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:36:53Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:36:55Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:36:57Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:37:07Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=93.39 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:37:03Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.39 helperRssMB=0.00 appHelperRssMB=93.39 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:37:05Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.39 helperRssMB=0.00 appHelperRssMB=93.39 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:37:07Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=93.39 helperRssMB=0.00 appHelperRssMB=93.39 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:37:16Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=59.98 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:37:12Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:37:14Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:37:16Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=59.98 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:41:49Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:41:45Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:41:47Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:41:49Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:41:59Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=93.70 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:41:54Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.70 helperRssMB=0.00 appHelperRssMB=93.70 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:41:56Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.61 helperRssMB=0.00 appHelperRssMB=93.61 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:41:59Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=93.61 helperRssMB=0.00 appHelperRssMB=93.61 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:42:08Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.02 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:42:04Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:42:06Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:42:08Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:46:12Z baseline

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `10`
- Evaluation: `status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.05 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:46:08Z phase=baseline sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:46:10Z phase=baseline sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:46:12Z phase=baseline sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:46:22Z idle

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.05 maxAppHelperRssMB=93.11 maxAppProcessCount=1 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:46:18Z phase=idle sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=93.11 helperRssMB=0.00 appHelperRssMB=93.11 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:46:20Z phase=idle sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=93.03 helperRssMB=0.00 appHelperRssMB=93.03 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:46:22Z phase=idle sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.05 appRssMB=93.03 helperRssMB=0.00 appHelperRssMB=93.03 appProcessCount=1 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```

## 2026-06-09T09:46:32Z quit

- Command: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- App binary: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`
- Samples: `3`, interval seconds: `2`, settle seconds: `5`
- Evaluation: `status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=60.06 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired`

```text
2026-06-09T09:46:27Z phase=quit sample=1 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.06 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:46:29Z phase=quit sample=2 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.06 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
2026-06-09T09:46:32Z phase=quit sample=3 coreaudiodCpuPercent=0.00 appCpuPercent=0.00 helperCpuPercent=0.00 appHelperCpuPercent=0.00 coreaudiodRssMB=60.02 appRssMB=0.00 helperRssMB=0.00 appHelperRssMB=0.00 appProcessCount=0 helperProcessCount=0 halProbeObserved=false phaseEventObserved=notRequired
```
