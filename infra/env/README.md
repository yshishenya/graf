# Production Environment Templates

This directory contains safe committed environment templates for 2brain Rec
deployment.

Templates may include variable names, placeholder markers, owners, rotation
expectations, and failure behavior. They must not include live secret values,
signed URLs, credential paths that expose private storage internals, or local
development defaults intended for production.
