# Security checklist

- [X] The fix preserves forced-RLS boundaries instead of bypassing RLS.
- [X] The session/device write retains request scope before flush.
- [X] Callback completion uses existing exact auth-bootstrap scope.
- [X] Tests cover both denied and permitted database contexts.
- [X] Evidence excludes email, code, token and session values.
