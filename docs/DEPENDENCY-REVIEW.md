# Dependency review

The release package was reviewed for third-party code before the licensing update.

| Component | What the package uses |
| --- | --- |
| Offline app | Inline JavaScript and CSS and browser APIs. No externally loaded scripts, vendored libraries, or package-manager manifests were found. |
| Python helper and tests | Python standard-library imports and the kit's own helper. The end-to-end test separately starts a locally installed Firefox. |
| JavaScript helper and tests | Node.js built-in modules. No npm packages were identified. |
| Training and evidence files | Original material and citations to published guidance. Cited publications retain their own terms. |

No bundled or imported GPLv3 or AGPLv3 library was identified. The review covers files and dependencies present in the release. It cannot establish the origin of every individual snippet supplied by an AI coding assistant. Firefox, Node.js, and Python are provided separately by the user and are outside the toolkit's license.

Before adding a library or copying a substantial code example, record its source and license. Confirm that those terms permit your intended distribution under the project's terms. Review the full license if there is any uncertainty about combining or redistributing code.
