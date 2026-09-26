# WeChat Local History Reader

Read-only export of message tables from a WeChat for Windows database that you own and can access locally. It creates newline-delimited JSON (JSONL) for local analysis or migration.

This is a community research tool, not an official WeChat SDK. Use it only with an account and local data you are authorized to access, and check applicable laws and service terms before use. Chat exports can contain sensitive personal information; keep them private and delete them when no longer needed.

## Scope

- Reads a configured account's local encrypted database and committed SQLite WAL snapshot.
- Checks the configured account alias against that account's local contacts database.
- Exports rows from `Msg_*` tables to a new JSONL file. Text-like fields are decoded when possible; undecodable binary values are preserved as base64.
- Opens the reconstructed database in memory and sets SQLite query-only mode.

It does not retrieve or extract keys, inspect or inject into a running WeChat process, automate the UI, send or forward messages, modify the source database, download attachments, or provide a hosted service. The user must already have a valid key and a separately obtained compatible decryption dependency. No account data, database, key, or chat export is included in this repository.

## Requirements

- Windows x64 and Python 3.12 x64 are the intended target. In this workspace only syntax and value-encoding checks ran under Python 3.13; a full export against a sample database has not been verified. Other platforms and client versions are not claimed as supported.
- A valid database key for the selected local account, supplied by the user in a private local key file.
- A compatible `WeChatDataAnalysis` source checkout containing `src/wechat_decrypt_tool/wechat_decrypt.py`. This repository does not redistribute that project's code; obtain it from its upstream source and review its license and provenance.
- Python dependency: `zstandard` (optional for decoding compressed message text; undecodable values remain base64).

The decryption helper exposes internal functions, so compatibility can change. Verify every dependency and client version yourself. There is no compatibility guarantee for another device, account, or release.

## Setup

Create a private config from the example and fill in paths for your own account. Keep the config and key file outside Git. The database path should be the account's `db_storage` directory, commonly under a per-account data directory. The key file is expected to contain an object keyed by your own account ID with a `db_key` hex string.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item config.example.json config.local.json
```

Edit `config.local.json` locally, then export to a new file outside the WeChat data directory:

```powershell
.\.venv\Scripts\python history_export.py --config config.local.json --out exports\history.jsonl
```

The command refuses to overwrite an existing output file. An interrupted export removes only the incomplete output file it created. Inspect the output path and its access permissions before sharing any exported data.

## Format

Each JSONL line contains the source message database name, hashed conversation table identifier, and the original row fields. Binary values that cannot be decoded are encoded as `{ "encoding": "base64", "data": "..." }`. This is a database-level export, not a normalized transcript: message types, media references, and client-specific fields may require further interpretation.

## Limitations

The tool reads all rows currently present in the selected `Msg_*` tables; it does not promise deleted-message recovery, media download, complete semantic decoding, or exact rendering as seen in the client. A database changing during snapshot capture may make an export fail safely; retry after the client has settled. Always validate the result against messages visible in your own client.

## Search terms

WeChat local chat history export, WeChat for Windows database reader, SQLite WAL snapshot, JSONL export, local archive, read-only message history, WCDB/SQLCipher-compatible database research.
