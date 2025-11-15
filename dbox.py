import requests
import dropbox
from dropbox.exceptions import ApiError
import json

APP_KEY = '0fcui56jhdh2lor'
APP_SECRET = '9wp5q2v360qip0p'
REFRESH_TOKEN = 'g6o3vCKI1_IAAAAAAAAAAd6cD1iLgck37FepCBz5TzDRRa38gag96fZ3aAH8NtBQ'
ACCESS_TOKEN = 'sl.u.AGEcyner1fwi_xo6A-Su6aoY0CssosZSmaWbARggcAzTZvOlRF9ibnZhxn2xXmb-HdjuzadOBYuib1Y8YMTft21p4mQ7a23UXyQH6-qjU04lkmBcDDE_BcutQ6qk5H4NN3-2DYHy1dE9ZGTfeLHb4964l6g1VZ5u9EB5l3LA6L2AYiLKCiojEndpjPVJXdOcbqTC4kB1noMgseGKgpwzZ7dpRsj59kov4NHY96gAYUyB-Mxsir7Q94aGAQDExAuYZDU96V8bUuVERXTXHMypQc9E93z8p8g9vbSFBZRJKUwXUdyDzzkDqvD-CmFWPnUOnbi2-9OGVdcRsL7YHIeZZ8ptng0RmT2L2Gj9WzuMq6RFqBBDgmGvwxKgxLK_-WrCApP7t2gzP5rfleZxUxXgBkiwx5mC7UNacHThukk7ssCEDa8bO1bExA_qEuX0lITQz8K1IEWcluGH0D3dh9e0vjizBK8RYZFoK82HIrtv2SSW_AWDbBBaqXoSnFgF8spMFvBa61MzYTxMEr_DeCFXdWSO01Usw8ujsgW1qcZfEXsOQNy2TAHN2e2k9gxqZaaHw9D6qmHJB_744bfQC6YjoqzRTHsWC91EpYu0Q7OPoZe5WOYteVTtGov17NUaXiajtLmPpnJyV0hM32aKYKuFiLBkn8FLTEzjLWxQKUQjQciGSUk9kFcr_bHEdDNQDuYBU6kpET7I8VDPmDIZvye_hyRMBcZkUs4f4WMCR46Qgfd3gMYZxw2p-GqC9yn6KTecB1T9pit4C39RhB3FZK9TSPLwUqefQKPqxk_t6CuKyGz7Hf4wHjDwGUDbdfFC9-VyvEGt33tPQqz_mqmZ5PScGdzjGGcSzFa5NRHZu2v1jet-y9JUL7XYDoGg0cCHuNsuieu-w7tk4xqCBGfcHAwSBwk6U2e8dB98CoBurhsdXGc-iINgn3elRcHGrLItwlTsT-BRyoK4QMICVdA5uCZD__Tg6AfKWMZFHBSf8x4at6In8CL4NHo4acKSiqbcjI62o7kBl6LaEwgJunAWAPwllYl1bWbgWvYNvAfmIMAK42IK_MrmOb8F2zhnDWTTfsU4YH-ZjUErla6xbDKR_BUpG5V9-HDM9qRsz2YQxaZx9xVbxaw6QfcSVID4gxre7L_JNiq3YuZnYlbV3KZo4WbLHalHUUNZqLzDwH610_1Fn-dvn0QYru-3WFxT_0mmEPrFXoDLtWScO0_ngthl92X8a0U9L2_fWfMcNtWcgxK9uHN7gODpIKYYGHosi5Q0On-KBCA'

dbx = dropbox.Dropbox(ACCESS_TOKEN)

def refresh_dropbox_token():
    token_url = "https://api.dropbox.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": APP_KEY,
        "client_secret": APP_SECRET,
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        expires_in = tokens.get("expires_in")  # время жизни токена в секундах
        print("Новый access token:", access_token)
        print("Expires in:", expires_in, "seconds")
        
        return access_token
    else:
        print("Ошибка при обновлении токена:", response.status_code, response.text)
        return None

#new_access_token = refresh_dropbox_token(APP_KEY, APP_SECRET, REFRESH_TOKEN)

def is_access_token_valid():
    """
    Проверяет валидность access_token для Dropbox.
    Возвращает True, если токен действителен, иначе False.
    """
    url = "https://api.dropboxapi.com/2/users/get_current_account"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.post(url, headers=headers)
    return response.status_code == 200

def list_folder(path=''):
    url = 'https://api.dropboxapi.com/2/files/list_folder'
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'path': path,
        'recursive': False,
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        entries = response.json().get('entries', [])
        rslt = []
        for entry in entries:
            print(f"{entry['.tag']}: {entry['name']}")
            rslt.append({'tag': entry['.tag'], 'name': entry['name']})
        return rslt
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None

def download_file(dropbox_path, local_path):
    url = "https://content.dropboxapi.com/2/files/download"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Dropbox-API-Arg": f'{{"path": "{dropbox_path}"}}'
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response.content)
        print(f"Файл сохранён как {local_path}")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

def upload_file(local_path, dropbox_path):
    url = "https://content.dropboxapi.com/2/files/upload"
    
    api_arg = json.dumps({
        "path": dropbox_path,
        "mode": "add",
        "autorename": True,
        "mute": False
    })

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Dropbox-API-Arg": api_arg,
        "Content-Type": "application/octet-stream"
    }

    with open(local_path, "rb") as f:
        data = f.read()
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        print(f"Файл {local_path} загружен на {dropbox_path}")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

def delete_path(dropbox_path):
    url = "https://api.dropboxapi.com/2/files/delete_v2"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"path": dropbox_path}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print(f"Путь {dropbox_path} удалён")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

def delete_file_if_exists(path: str):
    """
    Проверяет, существует ли файл по пути path в Dropbox, и удаляет его, если он есть.

    :param dbx: объект dropbox.Dropbox, авторизованный клиент
    :param path: путь к файлу в Dropbox (начинается с '/')
    """
    try:
        # Попытка получить метаданные файла
        dbx.files_get_metadata(path)
    except ApiError as err:
        if err.error.is_path() and err.error.get_path().is_not_found():
            # Файл не найден, ничего не делаем
            print(f"Файл {path} не найден, удаление не требуется.")
            return
        else:
            # Другая ошибка — пробрасываем дальше
            raise
    # Если метаданные получены, значит файл существует — удаляем
    dbx.files_delete_v2(path)
    print(f"Файл {path} удалён.")

def move_path(from_path, to_path):
    url = "https://api.dropboxapi.com/2/files/move_v2"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "from_path": from_path,
        "to_path": to_path
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print(f"{from_path} перемещён в {to_path}")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

def create_folder(path):
    url = "https://api.dropboxapi.com/2/files/create_folder_v2"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"path": path}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print(f"Папка {path} создана")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

if __name__ == '__main__':
    if is_access_token_valid():
        list_folder()
    else:
        refresh_dropbox_token()

