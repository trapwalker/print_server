import aiohttp
import asyncio
import cups
import json
import uuid
from aiohttp import ClientSession
from aiohttp.client_exceptions import ServerDisconnectedError, ClientConnectorError
from concurrent.futures import ThreadPoolExecutor
import logging
from dotenv import load_dotenv
from pathlib import Path
from os import getenv
import tempfile

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent

load_dotenv()

API_URL = TELEGRAM_API_TOKEN = getenv("API_URL", default="http://localhost:8000")
REG_PRINT_SERVER_URL = f'{API_URL}/reg/'
PRINT_JOB_URL_FORMAT = '{API_URL}/admin/printer/printjob/{task_id}'

PRINTER_NAME = "Your_Printer_Name"  # Можно задать конкретный принтер или выбрать из списка доступных
CONNECTION_RETRY_TIMEOUT = 5
FETCHING_JOBS_TIMEOUT = 5
MAX_PRINT_WORKERS = 1
DRY_RUN = False
# DRY_RUN = True

print_server_id = None
printers_data = None

def get_printers():
    conn = cups.Connection()
    printers = conn.getPrinters()
    return printers


def get_mac(delimiter=':'):
    mac_int = uuid.getnode()
    return delimiter.join(hex(b)[2:] for b in mac_int.to_bytes(6, byteorder='big'))


async def reg_station():
    global print_server_id, printers_data
    mac_address = get_mac()
    printers_data = get_printers()
    log.info('Mac-address: %s', mac_address)
    log.info('Printers %s found: %s', len(printers_data), ', '.join(printers_data.keys() or '...'))
    for name, info in printers_data.items():
        k_w = info and max(map(len, info.keys())) or 0
        log.debug('\t- %s:', name)
        for k, v in info.items():
            log.debug(f'\t\t{k:{k_w}}: {v}')

    async with aiohttp.ClientSession() as session:
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({'mac_address': mac_address, 'printers_data': printers_data,})
        async with session.post(REG_PRINT_SERVER_URL, data=payload, headers=headers) as response:
            log_func = log.info if response.status == 200 else log.error
            log_func('CALL POST %s: %s', REG_PRINT_SERVER_URL, response.status)
            answer = await response.json()
            print_server_id = answer.get('print_server_id')
            return answer


async def fetch_print_tasks(session: ClientSession):
    global print_server_id
    url = f'{API_URL}/srv/{print_server_id}/jobs'
    async with session.get(url) as response:
        return await response.json()


async def update_task_status(session: ClientSession, task_id, status, error_message=None):
    payload = {"task_id": task_id, "status": status, 'error_message': error_message}
    log.info('Update task #%s sratus to %s', task_id, status)
    try:
        async with session.post(f'{API_URL}/job/{task_id}/update', json=payload) as response:
            return await response.json()
    except Exception as e:
        log.error("Can't update status of task #%s to %s.%s", task_id, status, f' ({error_message})')


async def print_file(job, session: ClientSession):
    task_id = job['id']
    file_url = job['file']['url']
    file_name = job['file']['name']
    printer_name = job['printer']
    try:
        await update_task_status(session, task_id, status="PRINTING")
        with tempfile.NamedTemporaryFile(mode='w+b', suffix=f'__{file_name}') as fd:
            async with session.get(file_url) as response:
                while chunk := await response.content.read(1024):
                    fd.write(chunk)
            fd.seek(0)
            conn = cups.Connection()
            if DRY_RUN:
                log.info(
                    'PRINTING SUPPRESSED on %s: %s',
                    printer_name, PRINT_JOB_URL_FORMAT.format(**{**locals(), **globals()}),
                )
            else:
                conn.printFile(printer_name, fd.name, f"Print Job #{task_id}", {})
    except Exception as e:
        log.error('ERROR while job processing: %s', str(e))
        await update_task_status(session, task_id, status="COMPLETED_WITH_ERROR", error_message=str(e))
    else:
        await update_task_status(session, task_id, status="COMPLETED_SUCCESSFULLY")


async def async_print_file(job, session: ClientSession):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=MAX_PRINT_WORKERS) as pool:
        await loop.run_in_executor(pool, print_file, job, session)


TASKS_QUEUE = {}


async def main():
    global TASKS_QUEUE
    log.info('Print Service STARTED: %s', BASE_DIR)
    try_number = 0
    while True:
        try:
            log.info('Try to register on %s... %s', API_URL, try_number)
            await reg_station()
        except ClientConnectorError as e:
            log.error('Connection errror: %s', e)
        except Exception as e:
            log.exception(e)
        else:
            break
        try_number += 1
        await asyncio.sleep(CONNECTION_RETRY_TIMEOUT)

    async with ClientSession() as session:
        while True:
            log.debug('Check new tasks to printing...')
            jobs = []
            try:
                data = await fetch_print_tasks(session)
            except (ServerDisconnectedError, ClientConnectorError) as e:
                log.error('API server unavailable (%s): %s', API_URL, e)
            except Exception as e:
                log.exception(e)
            else:
                jobs = data.get('jobs', [])
                log.info('Tasks %s incoming', len(jobs))

            for job in jobs:
                TASKS_QUEUE[job['id']] = job

            while TASKS_QUEUE:
                _, current_job = TASKS_QUEUE.popitem()
                log.debug(
                    'Task #%(id)s (%(status)s) '
                    'to print %(copies)s copies of '
                    '%(file.name)r (%(file.url)s) '
                    'on %(printer)r',
                    flat_dict(job),
                )
                await print_file(job, session)

            await asyncio.sleep(FETCHING_JOBS_TIMEOUT)


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


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(name)-15s %(levelname)-8s %(message)s')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info('SERVICE TERMINATED')
