# Print Server

## Описание

Print Server — это сервис для печати документов. Он принимает задания на печать через API и отправляет их на указанный принтер. Проект использует Python и библиотеки aiohttp, pycups, python-dotenv для своей работы.

## Установка

Для установки склонируйте репозиторий и установите зависимости:

```bash
git clone https://github.com/trapwalker/print_server.git
cd print_server
pip install .
```

## Настройка

Перед запуском убедитесь, что в вашем файле `.env` заданы следующие переменные:
- `API_URL`: URL API для получения заданий на печать.
- `UID_FILE`: Путь к файлу с UID принтера.

Пример файла `.env`:

```
API_URL=http://localhost:8000
UID_FILE=.uid
```

## Запуск сервиса

Для запуска сервера используйте следующую команду:

```bash
python -m print_server
```

Сервис будет регистрироваться на указанном API, получать задания на печать и отправлять их на локальный принтер.

## Лицензия

Проект распространяется под BSD лицензией.

## Автор

Сергей Панков | svpmailbox@gmail.com
