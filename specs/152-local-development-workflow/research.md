# Research

Existing email-code auth already owns session, CSRF, tenant and device boundaries.
Production `__Host-` Secure cookies cannot work over plain HTTP loopback, so the
explicit local profile uses a separate cookie name. Existing dev Compose occupies
54329/9000/9001/8080; the local profile uses separate ports. Full processing is
intentionally not part of the daily UI loop.
