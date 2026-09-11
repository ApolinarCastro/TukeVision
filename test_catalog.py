import os
import json
import sys

os.environ['ENV_DVR_PRINCIPAL_CREDS'] = '{"username": "admin", "password": "WRONG_PASSWORD"}'

sys.path.insert(0, '.')
from src.domain.catalog import StoreCatalog

config = json.load(open('config/multistore.active.json'))
catalog = StoreCatalog.from_dict(config)

def cred_resolver(ref):
    creds = json.loads(os.environ.get(ref, '{}'))
    return creds.get('username', ''), creds.get('password', '')

entries = catalog.camera_descriptors(credential_resolver=cred_resolver)
for e in entries:
    print(f'{e.camera_id}: host={e.descriptor.host} user={e.descriptor.username} pass={e.descriptor.password[:3]}...')