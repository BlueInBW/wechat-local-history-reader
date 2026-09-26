"""Read stable copies of the selected account's encrypted DB and committed WAL."""
import hashlib
import hmac
import sqlite3
import struct
import sys
from pathlib import Path

from kit_config import load_config

def dependency_function(name, *args):
    source = Path(load_config()['decrypt_source'])
    if not (source/'wechat_decrypt_tool/wechat_decrypt.py').is_file():
        raise RuntimeError('Configure decrypt_source to the dependency src directory')
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from wechat_decrypt_tool import wechat_decrypt
    return getattr(wechat_decrypt, name)(*args)

def _resolve_page1_key_material(*args):
    return dependency_function('_resolve_page1_key_material', *args)

def _compute_page_hmac(*args):
    return dependency_function('_compute_page_hmac', *args)

def _decrypt_page(*args):
    return dependency_function('_decrypt_page', *args)



def checksum(data, endian, initial=(0, 0)):
    a, b = initial
    words = struct.unpack(endian + str(len(data) // 4) + 'I', data)
    for i in range(0, len(words), 2):
        a = (a + words[i] + b) & 0xffffffff
        b = (b + words[i + 1] + a) & 0xffffffff
    return a, b


def merge_wal(db, wal):
    result = bytearray(db)
    if not wal:
        return bytes(result)
    if len(wal) < 32:
        raise ValueError('Incomplete WAL header; retry')
    magic, version, size = struct.unpack('>III', wal[:12])
    if magic not in (0x377f0682, 0x377f0683) or version != 3007000 or size != 4096:
        raise ValueError('Unsupported WAL format')
    endian = '<' if magic == 0x377f0682 else '>'
    rolling = checksum(wal[:24], endian)
    if rolling != struct.unpack('>II', wal[24:32]):
        raise ValueError('Invalid WAL header checksum')
    frames, committed, db_pages = [], 0, 0
    for pos in range(32, len(wal) - 24 - size + 1, 24 + size):
        header, page = wal[pos:pos + 24], wal[pos + 24:pos + 24 + size]
        if header[8:16] != wal[16:24]:
            break
        next_sum = checksum(header[:8] + page, endian, rolling)
        if next_sum != struct.unpack('>II', header[16:24]):
            break
        rolling = next_sum
        number, count = struct.unpack('>II', header[:8])
        if not 1 <= number <= 262144 or count > 262144:
            raise ValueError('WAL page limit exceeded')
        frames.append((number, page))
        if count:
            committed, db_pages = len(frames), count
    for number, page in frames[:committed]:
        if number > db_pages:
            continue
        end = number * size
        if len(result) < end:
            result.extend(bytes(end - len(result)))
        if number == 1:
            page = db[:16] + page[16:]
        result[end - size:end] = page
    if committed:
        result = result[:db_pages * size]
    return bytes(result)


class SnapshotReader:
    def __init__(self, key):
        self.key = bytes.fromhex(key)
        self.material = {}
        self.cache = {}

    def read(self, path):
        path = Path(path)
        wal_path = Path(str(path) + '-wal')
        def read_pair():
            if path.stat().st_size > 1024 ** 3:
                raise ValueError('Database exceeds snapshot reader size limit')
            db = path.read_bytes()
            try:
                if wal_path.stat().st_size > 1024 ** 3:
                    raise ValueError('WAL exceeds snapshot reader size limit')
                wal = wal_path.read_bytes()
            except FileNotFoundError:
                wal = b''
            return db, wal
        first = read_pair()
        if first != read_pair():
            raise ValueError('Source changed during copy; retry')
        fingerprint = hashlib.sha256(first[0] + first[1]).digest()
        cached = self.cache.get(str(path))
        if cached and cached[0] == fingerprint:
            return cached[1]
        raw = merge_wal(*first)
        salt = raw[:16]
        if salt not in self.material:
            material = _resolve_page1_key_material(self.key, raw[:4096])
            if material is None:
                raise ValueError('Key does not match selected database')
            self.material[salt] = material
        enc, mac, _ = self.material[salt]
        plain = bytearray()
        for index in range(0, len(raw), 4096):
            page = raw[index:index + 4096]
            number = index // 4096 + 1
            if len(page) != 4096 or not hmac.compare_digest(page[-64:], _compute_page_hmac(mac, page, number)):
                raise ValueError(f'Database page validation failed: {number}')
            plain.extend(_decrypt_page(enc, page, number))
        # The copy is complete and has no external WAL. Only modify the in-memory copy.
        plain[18:20] = b'\x01\x01'
        conn = sqlite3.connect(':memory:')
        try:
            conn.deserialize(plain)
            if conn.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Snapshot integrity check failed')
            conn.execute('PRAGMA query_only=ON')
            conn.row_factory = sqlite3.Row
        except Exception:
            conn.close()
            raise
        if cached:
            cached[1].close()
        self.cache[str(path)] = fingerprint, conn
        return conn

    def close(self):
        for _, conn in self.cache.values():
            conn.close()
        self.cache.clear()
