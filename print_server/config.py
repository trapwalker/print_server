from pathlib import Path
from dotenv import load_dotenv
from os import getenv


BASE_DIR = Path(__file__).parent

load_dotenv()

API_URL = TELEGRAM_API_TOKEN = getenv("API_URL", default="http://admin.vestnik.press:8010")
REG_PRINT_SERVER_URL = f'{API_URL}/reg/'
PRINT_JOB_URL_FORMAT = '{API_URL}/admin/printer/printjob/{task_id}'
UID_FILE = Path(getenv("UID_FILE", default='.uid'))

CONNECTION_RETRY_TIMEOUT = 5
FETCHING_JOBS_TIMEOUT = 5
MAX_PRINT_WORKERS = 1
DRY_RUN = False
# DRY_RUN = True
