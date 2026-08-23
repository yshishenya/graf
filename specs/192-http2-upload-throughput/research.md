# Research: HTTP/2 upload throughput

## Decision 1: Tune the existing HTTP/2 request-body window

- **Decision**: Set the Nginx HTTP/2 body preread window to a bounded 2 МБ in the existing TLS server block.
- **Rationale**: Nginx defaults `http2_body_preread_size` to 64 КБ. With RTT around 165 ms that window caps one request stream near 3.2 Mbit/s, matching the observed 3.33 Mbit/s. A 2 МБ window is above the measured bandwidth-delay product and produced 34–38 Mbit/s synthetic HTTP/2 and 42.29 Mbit/s for the real file transfer.
- **Alternatives considered**: Keep 64 КБ (reproduces the incident); use an unbounded or much larger buffer (unnecessary memory exposure); force HTTP/1.1 (protocol workaround rather than fixing the active path).
- **Reference**: [Nginx `http2_body_preread_size`](https://nginx.org/en/docs/http/ngx_http_v2_module.html#http2_body_preread_size)

## Decision 2: Preserve server-mediated upload

- **Decision**: Keep WKWebView → Nginx → GRAF API → MinIO/DB/finalization unchanged.
- **Rationale**: Storage and finalization consumed only about 540 ms; they are not the bottleneck. Keeping the current path preserves authentication, authorization, validation, audit and secret custody while the edge-only change already delivers roughly 11.9× acceleration.
- **Alternatives considered**: Direct-to-MinIO/presigned upload, new CORS policy and client chunk scheduler. Rejected because they move trust boundaries, create lifecycle/retry work and solve a bottleneck that no longer exists.

## Decision 3: Reuse the existing safe installer

- **Decision**: Change only the repository site source and keep `install-billing-webhook-edge.sh` unchanged.
- **Rationale**: The installer already stages files, creates backups, checks Nginx syntax, reloads, probes health and edge behavior, and automatically restores backups on failure. Adding a second deployment path would increase operational risk.
- **Alternatives considered**: A dedicated upload-tuning installer or a new config-generation layer. Rejected as duplication.

## Decision 4: Validate with one focused assertion plus existing gates

- **Decision**: Use a direct source assertion, shell syntax, installer dry-run where safe, production evidence and the existing fast CI gate.
- **Rationale**: The behavior change is one declarative directive; a new test framework would cost more than the regression it prevents. Source presence plus Nginx validation and real upload evidence cover persistence, syntax and outcome.
- **Alternatives considered**: New integration-test service or synthetic load framework. Add only if future changes introduce dynamic edge generation or multiple tunable profiles.
