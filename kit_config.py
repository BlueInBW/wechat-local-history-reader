import json
import os
from pathlib import Path

def load_config(path=None):
    path = Path(path or os.environ.get('WECHAT_KIT_CONFIG', 'receiver.local.json')).resolve()
    os.environ['WECHAT_KIT_CONFIG'] = str(path)
    config = json.loads(path.read_text('utf-8-sig'))
    for field in ('source_directory','key_file','decrypt_source','database'):
        if field in config:
            value = Path(config[field])
            config[field] = str(value if value.is_absolute() else path.parent/value)
    config['_config_path'] = str(path)
    return config

def verify_source(config):
    root = Path(config['source_directory'])
    if not config.get('account') or not config.get('account_alias'):
        raise ValueError('Explicit account and alias required')
    if root.name != 'db_storage' or not root.parent.name.startswith(config['account']+'_'):
        raise PermissionError('Source path does not belong to configured account')

def load_key(config):
    keys = json.loads(Path(config['key_file']).read_text('utf-8-sig'))
    key = keys[config['account']]['db_key']
    if len(bytes.fromhex(key)) != 32:
        raise ValueError('Expected a 32-byte database key')
    return key
