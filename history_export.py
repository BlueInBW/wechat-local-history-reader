"""Export a user's own locally stored WeChat message databases as JSONL.

The program only reads database snapshots. It does not inspect or control a
WeChat process, collect keys, send messages, or change source database files.
"""
import argparse
import base64
import json
import re
from pathlib import Path

from db_source import SnapshotReader
from kit_config import load_config, load_key, verify_source


def json_safe(value, column=""):
    if isinstance(value, bytes):
        if column in {"message_content", "compress_content", "source"}:
            try:
                if value.startswith(b"\x28\xb5\x2f\xfd"):
                    import zstandard
                    value = zstandard.ZstdDecompressor().decompress(
                        value, max_output_size=16 * 1024 * 1024
                    )
                return value.decode("utf-8")
            except Exception:
                # Retain undecodable content losslessly without guessing a codec.
                pass
        return {"encoding": "base64", "data": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def export(config_path, output_path):
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    verify_source(config)
    root = Path(config["source_directory"]).resolve()
    output = Path(output_path).expanduser().resolve()
    if output == root or root in output.parents:
        raise ValueError("Choose an output path outside the WeChat source directory")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    contact_path = root / "contact" / "contact.db"
    reader = SnapshotReader(load_key(config))
    count = 0
    try:
        contacts = reader.read(contact_path)
        row = contacts.execute(
            "SELECT alias FROM contact WHERE username=?", (config["account"],)
        ).fetchone()
        if not row or row[0] != config["account_alias"]:
            raise PermissionError("Configured account alias does not match the local database")

        sources = sorted(
            path for path in (root / "message").glob("message_*.db")
            if re.fullmatch(r"message_\d+\.db", path.name)
        )
        if not sources:
            raise FileNotFoundError("No local message_*.db files found")

        # Exclusive creation prevents accidental overwrite. If an error occurs,
        # remove only the incomplete output created by this invocation.
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            try:
                for source in sources:
                    db = reader.read(source)
                    tables = [
                        item[0] for item in db.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                        )
                        if re.fullmatch(r"Msg_[a-f0-9]{32}", item[0])
                    ]
                    for table in tables:
                        columns = [item[1] for item in db.execute(f"PRAGMA table_info([{table}])")]
                        for row in db.execute(f"SELECT * FROM [{table}] ORDER BY local_id"):
                            record = {
                                "database": source.name,
                                "table": table,
                                "conversation_id_hash": table[4:],
                                "message": {
                                    key: json_safe(row[key], key) for key in columns
                                },
                            }
                            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                            count += 1
            except Exception:
                stream.close()
                output.unlink(missing_ok=True)
                raise
    finally:
        reader.close()

    return count, output


def main():
    parser = argparse.ArgumentParser(
        description="Export messages from your own local WeChat database to JSON Lines."
    )
    parser.add_argument("--config", required=True, help="Path to your private JSON config")
    parser.add_argument("--out", required=True, help="New JSONL file path; existing files are never overwritten")
    args = parser.parse_args()
    count, path = export(args.config, args.out)
    print(json.dumps({"exported_messages": count, "output": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
