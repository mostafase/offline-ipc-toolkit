# Contributing

## Report a problem or suggest an improvement

Use the relevant GitHub issue template. Include the toolkit version, device and browser, and the steps you took. Use Practice mode or fictional data in examples. Keep patient and staff information, real facility records, backup files, and credentials out of reports. For a potential security issue, follow [the security policy](SECURITY.md).

## Propose a change

1. Open an issue first for changes to clinical workflows, calculations, evidence, or translations.
2. Keep the pull request focused. Describe what changed and what you tested. For clinical content, cite the source and section and identify facility-configurable choices. For translated clinical text, say whether a fluent IPC reviewer checked it.
3. Check the affected workflow offline. For code changes, run `node tests/test_core.js` and `python -m unittest discover -s tests -p test_ipc_tool.py`. If printable or embedded guide content changed, run `python tools/sync_embedded_kit.py` and check the standalone and embedded versions.
4. Submit only material you have permission to contribute. Identify third-party code or content and its license. The toolkit's code and original training content use separate licenses described in [LICENSE.md](LICENSE.md).

Accessibility reports are welcome. See [ACCESSIBILITY.md](ACCESSIBILITY.md) for what to include.
