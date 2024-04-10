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
from pprint import pprint


log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent

load_dotenv()

API_URL = TELEGRAM_API_TOKEN = getenv("API_URL", default="http://localhost:8000")

UPDATE_STATUS_URL = "http://example.com/api/update_status"  # URL для обновления статуса задачи
PRINTER_NAME = "Your_Printer_Name"  # Можно задать конкретный принтер или выбрать из списка доступных
CONNECTION_RETRY_TIMEOUT = 5
FETCHING_JOBS_TIMEOUT = 5


print_server_id = None
printers_data = None

def get_printers():
    conn = cups.Connection()
    printers = conn.getPrinters()
    return printers


def get_mac(delimiter=':'):
    mac_int = uuid.getnode()
    return delimiter.join(hex(b)[2:] for b in mac_int.to_bytes(6, byteorder='big'))


async def reg_station(api_url):
    global print_server_id, printers_data
    url = f'{api_url}/reg/'
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
        async with session.post(url, data=payload, headers=headers) as response:
            response_text = await response.text()
            log_func = log.info if response.status == 200 else log.error
            log_func('CALL POST %s: %s', url, response.status)
            answer = await response.json()
            print_server_id = answer.get('print_server_id')
            return answer


async def fetch_print_tasks(session: ClientSession):
    global print_server_id
    url = f'{API_URL}/srv/{print_server_id}/jobs'
    async with session.get(url) as response:
        return await response.json()


async def update_task_status(session: ClientSession, task_id, status):
    payload = {"task_id": task_id, "status": status}
    async with session.post(UPDATE_STATUS_URL, json=payload) as response:
        return await response.json()


async def print_file(file_path, task_id, session: ClientSession):
    try:
        conn = cups.Connection()
        conn.printFile(PRINTER_NAME, file_path, "Print Job", {})
        await update_task_status(session, task_id, "printed")
    except Exception as e:
        await update_task_status(session, task_id, f"error: {str(e)}")


# Асинхронная обертка для функции печати
async def async_print_file(file_path, task_id, session: ClientSession):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, print_file, file_path, task_id, session)


TASKS_QUEUE = {}


async def main():
    global TASKS_QUEUE
    log.info('Print Service STARTED: %s', BASE_DIR)
    try_number = 0
    while True:
        try:
            log.info('Try to register on %s... %s', API_URL, try_number)
            await reg_station(API_URL)
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
                print(job)

            await asyncio.sleep(FETCHING_JOBS_TIMEOUT)
            # await async_print_file(task['file_path'], task['task_id'], session)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(name)-15s %(levelname)-8s %(message)s')
    asyncio.run(main())

