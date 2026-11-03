#!/bin/sh
case "$#:$1" in
    1:--tick|1:--witness) exec /usr/local/libexec/billing-observation-probe.sh "$1" ;;
    *) printf '%s\n' '{"schema_version":1,"result_code":"observation_unavailable"}'; exit 1 ;;
esac
