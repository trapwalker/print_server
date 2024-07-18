import random
import socket
import logging

from print_server import config


log = logging.getLogger(__name__)


def get_external_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '<UNKNOWN>'
    return ip


def get_mac(delimiter=':'):
    try:
        uid = int(config.UID_FILE.read_text().strip())
    except Exception:
        log.info(f'UID-file not found by {config.UID_FILE!r}. Generate new.')
        uid = int.from_bytes(random.randbytes(6), byteorder='big')
        config.UID_FILE.write_text(str(uid))

    mac = uid
    return delimiter.join(hex(b)[2:].zfill(2) for b in mac.to_bytes(6, byteorder='big'))


def flat_dict(d_in, d_out=None, prefix=''):
    d_out = d_out or {}
    for k, v in d_in.items():
        if isinstance(v, dict):
            try:
                flat_dict(v, d_out, prefix=f'{prefix}{k}.')
            except:
                pass
            else:
                continue
        d_out[f'{prefix}{k}'] = v
    return d_out
