import aiohttp
import asyncio
import cups
import json
from aiohttp import ClientSession
from aiohttp.client_exceptions import ServerDisconnectedError, ClientConnectorError
import tempfile
import socket
from loguru import logger as log
import sys
from pathlib import Path
from platformdirs import user_log_dir

from print_server import config
from print_server.tools import get_external_ip, get_mac, flat_dict


PROD_LOG_DIR = Path(user_log_dir(appname='print_server'))
LOG_DIR = Path('log') if Path('log').is_dir() else PROD_LOG_DIR

print_server_id = None
printers_data = None


def get_printers():
    conn = cups.Connection()
    printers = conn.getPrinters()
    return printers


async def reg_station():
    global print_server_id, printers_data
    mac_address = get_mac()
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = '<UNKNOWN>'

    ip = get_external_ip()

    printers_data = get_printers()
    log.info('Register {!r} (uid={}, ip={})', hostname, mac_address, ip)
    log.info('Printers {} found: {}', len(printers_data), ', '.join(printers_data.keys() or '...'))
    for name, info in printers_data.items():
        k_w = info and max(map(len, info.keys())) or 0
        log.debug('\t- {}:', name)
        for k, v in info.items():
            log.debug(f'\t\t{k:{k_w}}: {v}')

    async with aiohttp.ClientSession() as session:
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({
            'mac_address': mac_address,
            'hostname': hostname,
            'ip': ip,
            'printers_data': printers_data,
        })
        async with session.post(config.REG_PRINT_SERVER_URL, data=payload, headers=headers) as response:
            log_func = log.info if response.status == 200 else log.error
            log_func(f'CALL POST {config.REG_PRINT_SERVER_URL}: {response.status}')
            answer = await response.json()
            print_server_id = answer.get('print_server_id')
            return answer


async def fetch_print_tasks(session: ClientSession):
    global print_server_id
    url = f'{config.API_URL}/srv/{print_server_id}/jobs'
    async with session.get(url) as response:
        return await response.json()


async def update_task_status(session: ClientSession, task_id, status, error_message=None):
    payload = {"task_id": task_id, "status": status, 'error_message': error_message}
    log.info('Update task #{} sratus to {}...', task_id, status)
    try:
        async with session.post(f'{config.API_URL}/job/{task_id}/update', json=payload) as response:
            result = await response.json()
            log.info('Task #{} sratus updating to {} result: {}', task_id, status, result)
            return result
    except Exception as e:
        log.error("Can't update status of task #{} to {}.{}: {}", task_id, status, f' ({error_message})', e)


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
            if config.DRY_RUN:
                log.info(
                    'PRINTING SUPPRESSED on {}: {}',
                    printer_name, config.PRINT_JOB_URL_FORMAT.format(**{**locals(), **globals()}),
                )
            else:
                conn = cups.Connection()
                conn.enablePrinter(printer_name)
                conn.printFile(
                    printer_name, fd.name,
                    f"Print Job #{task_id}",
                    {'copies': str(job['copies'])},
                )
    except Exception as e:
        log.error('ERROR while job processing: {}', str(e))
        await update_task_status(session, task_id, status="COMPLETED_WITH_ERROR", error_message=str(e))
    else:
        await update_task_status(session, task_id, status="COMPLETED_SUCCESSFULLY")


TASKS_QUEUE = {}


async def main():
    global TASKS_QUEUE
    log.info('Print Service STARTED: {}', config.BASE_DIR)
    try_number = 0
    while True:
        try:
            log.info('Try to register on {}... {}', config.API_URL, try_number)
            await reg_station()
        except ClientConnectorError as e:
            log.error('Connection errror: {}', e)
        except Exception as e:
            log.exception(e)
        else:
            break
        try_number += 1
        await asyncio.sleep(config.CONNECTION_RETRY_TIMEOUT)

    async with ClientSession() as session:
        while True:
            # log.debug('Check new tasks to printing...')
            jobs = []
            try:
                data = await fetch_print_tasks(session)
            except (ServerDisconnectedError, ClientConnectorError) as e:
                log.error('API server unavailable ({}): {}', config.API_URL, e)
            except Exception as e:
                log.exception(e)
            else:
                jobs = data.get('jobs', [])
                if jobs:
                    log.info('Tasks {} incoming', len(jobs))

            for job in jobs:
                TASKS_QUEUE[job['id']] = job

            while TASKS_QUEUE:
                _, current_job = TASKS_QUEUE.popitem()
                log.debug(
                    f'Task #{job["id"]} ({job["status"]}) '
                    f'to print {job["copies"]} copies of '
                    f'{job["file"]["name"]} ({job["file"]["url"]}) '
                    f'on {job["printer"]}',
                )
                await print_file(job, session)

            await asyncio.sleep(config.FETCHING_JOBS_TIMEOUT)


if __name__ == '__main__':
    log.configure(
        handlers=[
            dict(
                sink=sys.stdout, colorize=True,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>"
            ),
            dict(
                sink=LOG_DIR / "error.log", backtrace=True, diagnose=True, level="ERROR",
                rotation="00:00", retention=10,
            ),
            dict(sink=LOG_DIR / "all.log", rotation="00:00", retention=10),
        ],
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info('SERVICE TERMINATED')
