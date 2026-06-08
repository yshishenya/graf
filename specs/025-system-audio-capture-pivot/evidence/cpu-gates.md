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
