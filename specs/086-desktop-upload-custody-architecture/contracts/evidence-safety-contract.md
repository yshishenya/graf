# Evidence Safety Contract

086 evidence is metadata-only.

## Allowed Evidence

- File paths already present in the repository.
- Line counts and function/type names.
- Public route names and operation ids.
- Safe status names, copy keys, and reason codes.
- Test file names and command names.
- Dependency and entrypoint names.

## Prohibited Evidence

- Raw audio or transcript content.
- Private meeting titles or participant data.
- API keys, tokens, signed URLs, passwords, or credential paths.
- Private local filesystem paths from a real user's machine.
- Full diagnostic payloads copied from real incidents.

## Review Rule

Before committing audit docs, run a placeholder/secret-oriented scan over the
new 086 artifacts and manually inspect any suspicious evidence.
