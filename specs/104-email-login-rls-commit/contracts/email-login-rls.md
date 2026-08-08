# Email-login RLS contract

- `auth_session_device_bindings` is inserted only under exact request context.
- `auth_callback_states` completion and its auth audit are committed only under
  exact auth-bootstrap context for the resolved workspace/user.
- Neither context may access another workspace.
