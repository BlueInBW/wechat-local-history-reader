# Technical path

This package is deliberately limited to reading message databases already present on the user's own computer. It requires the user to provide a database key and a compatible decryption dependency; it does not explain or implement key acquisition.

1. The configuration names one account, its local `db_storage` directory, a private key-file path, and the path to a separately obtained decryption dependency.
2. Before exporting, the program checks the configured account alias against the local contact database. It rejects paths that do not appear to belong to the configured account.
3. It copies the database and WAL bytes in memory and reads the pair twice. If either file changes during capture, it stops rather than exporting a potentially inconsistent snapshot.
4. The snapshot reader validates committed WAL frames and page authentication, decrypts pages using the user-provided key and external helper, then deserializes the result into an in-memory SQLite connection with `query_only` enabled.
5. The exporter visits tables named `Msg_` plus a 32-character hexadecimal identifier and writes each row as a JSONL record. It leaves undecodable binary data in base64 so the export does not silently discard it.
6. Output creation is exclusive: existing files are not overwritten. On an error, only the partial output created by that invocation is removed.

## Compatibility

The snapshot/WAL and JSONL flow may be reusable when database layout and encryption behavior remain compatible. A different account still needs its own local path and matching key. A different device can use different data paths, keys, architecture, and client state. A different client release may change the database format or table schema. This repository contains no automatic version bypass and makes no cross-version compatibility promise.

## Privacy and safety boundary

The exported file may contain private conversations, identifiers, and media references. It stays on the user's machine unless the user chooses to share it. Never commit configs, keys, database files, logs containing message bodies, or export files. The repository includes no real chat data or credentials. This project does not control WeChat, send messages, or claim to avoid platform monitoring.

## External dependency

The integration loads internal page-decryption functions from a separately obtained `WeChatDataAnalysis` source checkout. That source is not vendored here. Review the upstream project's license, source, and version before use; compatibility and security are not guaranteed by this package.
