import json
import os
from time import sleep

import apiclient
import httplib2
import googleapiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials

# Файл, полученный в Google Developer Console
from MessagePack.message import err_log

CREDENTIALS_FILE = os.environ.get('GOOGLE_CREDENTIALS_FILE')


def get_credentials():
    global CREDENTIALS_FILE
    if CREDENTIALS_FILE is None:
        CREDENTIALS_FILE = os.environ.get('GOOGLE_CREDENTIALS_FILE')
    return CREDENTIALS_FILE


def get_service():
    """ Авторизуемся и получаем service — экземпляр доступа к API. """
    service = None
    cred_path = None
    try:
        cred_path = get_credentials()
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            cred_path,
            ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive'])
        http_auth = credentials.authorize(httplib2.Http())
        service = googleapiclient.discovery.build('sheets', 'v4', http=http_auth)
    except Exception as e:
        err_log('get_service [g_spreadsheets]:', cred_path + str(e))
        print(f'unable to get google api service client, CREDENTIALS_FILE: {cred_path}', str(e))
    return service


def get_drive_service():
    service = None
    try:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive'])
        http_auth = credentials.authorize(httplib2.Http())
        service = apiclient.discovery.build('drive', 'v3', http=http_auth)
    except Exception as e:
        print(f'unable to get google api drive service client, CREDENTIALS_FILE: {CREDENTIALS_FILE}, ', str(e))
    return service


def check_spreadsheet(url):
    service = get_service()
    spreadsheet_id = get_spreadsheet_id(url)
    range_ = 'A1:B2'
    return get_data_from_sheet(service, spreadsheet_id, range_)


def get_data_from_sheet(service, spreadsheet_id, range_=None, major_dimension='ROWS'):
    if service is None:
        print(f'invalid google api service client: {service}')
        return None
    if spreadsheet_id is None:
        print(f'invalid spreadsheet_id: {spreadsheet_id}')
        return None
    values = None
    try:
        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_,
            majorDimension=major_dimension
        ).execute()
    except Exception as e:
        print(f'unable to get spreadsheet data, spreadsheet id: {spreadsheet_id}, ', str(e))
    return values


def get_spreadsheet_id(url):
    """returns the id of the Google Sheets document"""
    sh_id = None
    try:
        sh_id = url.split('/edit')[0].split('/')[-1]
    except Exception as e:
        print('unable to get spreadsheet id, ', str(e))
    return sh_id


def get_credentials_email():
    """return email link for spreadsheet edit access"""
    email = None
    try:
        with open(CREDENTIALS_FILE) as f:
            email = json.loads(f.read())['client_email']
    except Exception as e:
        print('unable to get client email, ', str(e))
    return email


def get_range(from_, to_):
    """ Return string in format [letter][number]:[letter][number] for Google Sheets range setup.
    Input data with count from 1, if < 1 - set to 1. """
    from_[0] = 1 if from_[0] < 1 else from_[0]
    if from_[1] is None:
        from_[1] = ''
    else:
        from_[1] = 1 if from_[1] < 1 else from_[1]
    to_[0] = 1 if to_[0] < 1 else to_[0]
    if to_[1] is None:
        to_[1] = ''
    else:
        to_[1] = 1 if to_[1] < 1 else to_[1]
    r_list = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
              'U', 'V', 'W', 'X', 'Y', 'Z']
    range_ = f"{r_list[from_[0] - 1]}{from_[1]}:{r_list[to_[0] - 1]}{to_[1]}"
    return range_


def add_text_to_sheet(service, spreadsheet_id, data, range_, major_dimension='ROWS'):
    if service is None:
        print(f'invalid google api service client: {service}')
        return False
    if spreadsheet_id is None:
        print(f'invalid spreadsheet_id: {spreadsheet_id}')
        return False
    if len(data) == 0:
        print(f'invalid incoming data: {data}')
        return False
    try:
        values = service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": range_,
                     "majorDimension": major_dimension,
                     "values": data},
                ]
            }
        ).execute()
        return True
    except Exception as e:
        print(f'unable to add data to spreadsheet, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def insert_rows_or_columns(service, spreadsheet_id, data, start_index, major_dimension='ROWS', sheet_id='0'):
    if service is None:
        print(f'invalid google api service client: {service}')
        return False
    if spreadsheet_id is None:
        print(f'invalid spreadsheet_id: {spreadsheet_id}')
        return False
    if len(data) == 0:
        print(f'invalid incoming data: {data}')
        return False
    try:
        end_index = start_index + len(data)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [
                    {
                        'insertDimension': {
                            'range': {
                                'sheetId': sheet_id,
                                'dimension': major_dimension,
                                'startIndex': start_index,
                                'endIndex': end_index
                            }
                        }
                    }
                ]
            }
        ).execute()
        if major_dimension in ['ROWS', 'COLUMNS']:
            length = 0
            for d in data:
                if len(d) > length:
                    length = len(d)
            if major_dimension == 'ROWS':
                range_ = get_range([1, start_index + 1], [length + 1, start_index + len(data)])
            else:
                range_ = get_range([start_index + 1, 1], [start_index + len(data), length + 1])
            add_text_to_sheet(service, spreadsheet_id, data, range_, major_dimension)
        return True
    except Exception as e:
        print(f'unable to insert data to spreadsheet, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def create_spreadsheet():
    """Создает новую таблицу с указанным названием и указанными параметрами доступа"""
    service = get_service()
    try:
        spreadsheet = service.spreadsheets().create(body={
            'properties': {'title': 'Create Test', 'locale': 'ru_RU'},
            'sheets': [{'properties': {'sheetType': 'GRID',
                                       'sheetId': 0,
                                       'title': 'Сие есть название листа',
                                       'gridProperties': {'rowCount': 30000, 'columnCount': 20}}}]
        }).execute()
    except Exception as e:
        print(f'unable to create spreadsheet,', str(e))
        return False
    drive_service = get_drive_service()
    try:
        share_res = drive_service.permissions().create(
            fileId=spreadsheet['spreadsheetId'],
            body={'type': 'user', 'role': 'writer', 'emailAddress': 'gorod.old@gmail.com'},
            fields='id'
        ).execute()
        return True
    except Exception as e:
        print(f'unable to set access permission,', str(e))
        return False


def delete_sheet(spreadsheet_id, sheet_id, service=None):
    """Удаляет лист из таблицы по ID"""
    if service is None:
        service = get_service()
    try:
        request_body = {
            'requests': [{
                "deleteSheet": {
                    "sheetId": sheet_id
                }
            }]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
        return True
    except Exception as e:
        print(f'unable to delete sheet id={sheet_id}, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def add_sheet(spreadsheet_id, col_count=None, service=None):
    """Создает еще один лист в таблице (spreadsheet_id) с названием "Лист {len(sheets) + 1}"
    и указанным количеством столбцов (col_count)."""
    col_count = 26 if col_count is None else col_count
    if service is None:
        service = get_service()
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets')
        add_id = 0
        for sheet in sheets:
            sheet_id = sheet.get('properties').get('sheetId')
            if sheet_id >= add_id:
                add_id = sheet_id + 1
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': f'Лист {len(sheets) + 1}',
                        'sheetType': 'GRID',
                        'sheetId': add_id,
                        'gridProperties': {'rowCount': 1000, 'columnCount': col_count},
                        'tabColor': {
                            'red': 0.44,
                            'green': 0.99,
                            'blue': 0.50
                        }
                    }
                }
            }]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
    except Exception as e:
        print(f'unable to add sheet, spreadsheet id: {spreadsheet_id}, ', str(e))


def insert_sheet(spreadsheet_id, col_count=None, service=None):
    """Вставляет новый лист по индексу 0 с названием "Лист 1",
    переименовывает последующие листы по порядку Лист 2, Лист 3 ... и тд."""
    col_count = 26 if col_count is None else col_count
    if service is None:
        service = get_service()
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets')
        # rename sheets
        insert_id = 0
        requests = []
        i = len(sheets)
        for sheet in reversed(sheets):
            sheet_id = sheet.get('properties').get('sheetId')
            if sheet_id >= insert_id:
                insert_id = sheet_id + 1
            prop = {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'title': f'Лист {i + 1}'
                    },
                    "fields": "title"
                }
            }
            requests.append(prop)
            i -= 1
        # insert sheet
        requests.append({
            'addSheet': {
                'properties': {
                    'title': 'Лист 1',
                    'sheetType': 'GRID',
                    'sheetId': insert_id,
                    'index': 0,
                    'gridProperties': {'rowCount': 1000, 'columnCount': col_count},
                    'tabColor': {
                        'red': 0.44,
                        'green': 0.99,
                        'blue': 0.50
                    }
                }
            }
        })
        request_body = {'requests': requests}
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
    except Exception as e:
        print(f'unable to insert sheet, spreadsheet id: {spreadsheet_id}, ', str(e))


def resize_sheet(spreadsheet_id, sheet_id, row_count, col_count):
    """Изменяет максимальное количество строк и столбцов в листе таблицы"""
    service = get_service()
    try:
        request_body = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "gridProperties": {
                                "rowCount": row_count,
                                "columnCount": col_count
                            },
                            "sheetId": sheet_id
                        },
                        "fields": "gridProperties"
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
        return True
    except Exception as e:
        print(f'unable to add sheet id={sheet_id}, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def append_dimension(spreadsheet_id, sheet_id, last_index, count, pixel_size, service=None, dimension='ROWS'):
    """Добавляет указанное количество (count) строк или столбцов (dimension) по индексу (last_index)
    и задает им размер высота или ширина соответственно (pixel_size)"""
    if service is None:
        service = get_service()
    try:
        request_body = {
            "requests": [
                {
                    "appendDimension": {
                        "sheetId": sheet_id,
                        "dimension": dimension,
                        "length": count
                    },
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": last_index + 1,
                            "endIndex": last_index + count
                        },
                        "properties": {
                            "pixelSize": pixel_size
                        },
                        "fields": "pixelSize"
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
        return True
    except Exception as e:
        print(f'unable to append dimension sheet id={sheet_id}, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def delete_dimension(spreadsheet_id, sheet_id, start_index, end_index, service=None, dimension='ROWS'):
    """Удаляет определенное количество (start_index, end_index) строк или столбцов (dimension)
    в таблице (spreadsheet_id) на листе (sheet_id)."""
    if service is None:
        service = get_service()
    try:
        request_body = {
            "requests": [
                {
                    "deleteDimension": {
                        'range': {
                            "sheetId": sheet_id,
                            "dimension": dimension,
                            "startIndex": start_index,
                            "endIndex": end_index
                        }
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
        return True
    except Exception as e:
        print(f'unable to delete dimension sheet id={sheet_id}, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def set_row_size(spreadsheet_id, sheet_id, start_index, end_index, pixel_size):
    service = get_service()
    try:
        request_body = {
            "requests": [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_index,
                            "endIndex": end_index
                        },
                        "properties": {
                            "pixelSize": pixel_size
                        },
                        "fields": "pixelSize"
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
        return True
    except Exception as e:
        print(f'unable to set row size, sheet id={sheet_id}, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def set_row_color(spreadsheet_id, sheet_id, start_index, end_index, col_count):
    service = get_service()
    try:
        request_body = {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_index,
                            "endRowIndex": end_index,
                            "startColumnIndex": 0,
                            "endColumnIndex": col_count
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.96,
                                    "green": 0.93,
                                    "blue": 0.85
                                }
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()
        return True
    except Exception as e:
        print(f'unable to set header background, sheet id={sheet_id}, spreadsheet id: {spreadsheet_id}, ', str(e))
        return False


def insert_spreadsheet_data(data, spreadsheet_id, header, limit_per_sheet: int = 400000,
                            chunk_size=40000, service=None):
    if data is None or len(data) == 0:
        print(f'[insert_spreadsheet_data] incoming data is empty: {data}')
        return
    if len(header) == 0:
        print(f'[add_spreadsheet_data] invalid header: {header}')
        return
    if limit_per_sheet > 400000:
        limit_per_sheet = 400000
    if chunk_size > 40000:
        chunk_size = 40000
    if service is None:
        service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    sheet = sheets[0]
    sheet_id = sheet.get('properties').get('sheetId')
    sheet_name = sheet.get('properties').get('title')
    row_limit = sheet.get('properties').get('gridProperties').get('rowCount')
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name + '!' + 'A1:B',
        majorDimension='ROWS'
    ).execute()
    rows = values.get('values')
    count = len(rows) if rows else 0
    insert_index = 1
    if rows and '[INFO]' in rows[len(rows) - 1][0]:
        delete_dimension(spreadsheet_id, sheet_id, count - 1, count, service)
        count -= 1
        row_limit -= 1
    if count == 0:
        insert_index = 0
        index = len(data) - limit_per_sheet + 1 if limit_per_sheet <= len(data) else 0
        data.insert(index, header)
    data_ = None
    if limit_per_sheet < count + len(data):
        index = count + len(data) - limit_per_sheet
        data_ = data[0:index]
        data = data[index:]
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        range_ = get_range([1, insert_index + 1], [len(header) + 1, insert_index + len(chunk)])
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [
                    {
                        'insertDimension': {
                            'range': {
                                'sheetId': sheet_id,
                                'dimension': 'ROWS',
                                'startIndex': insert_index,
                                'endIndex': insert_index + len(chunk)
                            }
                        }
                    }
                ]
            }
        ).execute()
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": sheet_name + '!' + range_,
                     "majorDimension": 'ROWS',
                     "values": chunk},
                ]
            }
        ).execute()
        insert_index += len(chunk)
    set_row_size(spreadsheet_id, sheet_id, 1, count + len(data), 21)
    set_row_color(spreadsheet_id, sheet_id, 0, 1, len(header))
    count = count + len(data)
    row_limit = 1000 if count < 1000 else count
    resize_sheet(spreadsheet_id, sheet_id, row_limit, len(header))
    if data_:
        print('[insert_spreadsheet_data] insert new sheet')
        insert_sheet(spreadsheet_id, len(header), service)
        insert_spreadsheet_data(data_, spreadsheet_id, header, limit_per_sheet, chunk_size, service)


def add_spreadsheet_data(data, spreadsheet_id, header, limit_per_sheet: int = 400000,
                         chunk_size=40000, service=None, end_row: str = None):
    """Дописывает данные в последний лист таблицы в конец, если лимиты не позволяют
    создает еще один лист с названием "Лист {len(sheets) + 1}"."""
    data = [] if data is None else data
    if not end_row and len(data) == 0:
        print(f'[add_spreadsheet_data] incoming data is empty: {data}')
        return
    if len(header) == 0:
        print(f'[add_spreadsheet_data] invalid header: {header}')
        return
    if limit_per_sheet > 400000:
        limit_per_sheet = 400000
    if chunk_size > 40000:
        chunk_size = 40000
    if service is None:
        service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    sheet = sheets[-1]
    sheet_id = sheet.get('properties').get('sheetId')
    sheet_name = sheet.get('properties').get('title')
    row_limit = sheet.get('properties').get('gridProperties').get('rowCount')
    col_limit = sheet.get('properties').get('gridProperties').get('columnCount')
    if col_limit > len(header):
        resize_sheet(spreadsheet_id, sheet_id, row_limit, len(header))
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name + '!' + 'A1:B',
        majorDimension='ROWS'
    ).execute()
    rows = values.get('values')
    count = len(rows) if rows else 0
    if rows and '[INFO]' in rows[len(rows) - 1][0]:
        delete_dimension(spreadsheet_id, sheet_id, count - 1, count, service)
        count -= 1
        row_limit -= 1
    if count == 0:
        data.insert(0, header)
        set_row_color(spreadsheet_id, sheet_id, 0, 1, len(header))
    if end_row and (len(data) == 0 or '[INFO]' not in str(data[len(data) - 1][0])):
        data.append(['[INFO] ' + end_row])
    data_ = None
    if limit_per_sheet < count + len(data):
        data_ = data[limit_per_sheet - count:]
        data = data[0:limit_per_sheet - count]
    if row_limit < count + len(data):
        expand = count + len(data) - row_limit
        append_dimension(spreadsheet_id, sheet_id, row_limit - 1, expand, 21, service)
    if end_row and not data_:
        set_row_color(spreadsheet_id, sheet_id, len(data) + count - 1, len(data) + count, len(header))
    set_row_size(spreadsheet_id, sheet_id, 1, count + len(data), 21)
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        range_ = get_range([1, count + 1], [len(header), len(chunk) + count + 1])
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": sheet_name + '!' + range_,
                     "majorDimension": 'ROWS',
                     "values": chunk},
                ]
            }
        ).execute()
        count += len(chunk)
    if data_:
        print('[add_spreadsheet_data] add new sheet')
        add_sheet(spreadsheet_id, len(header), service)
        add_spreadsheet_data(data_, spreadsheet_id, header, limit_per_sheet, chunk_size, service, end_row)


def add_data_to_sheet_by_name(data, spreadsheet_id, sheet_name, header, limit_per_sheet: int = 400000,
                              chunk_size=40000, service=None, end_row: str = None):
    """Дописывает данные в лист по названию sheet_name в конец, если лимиты не позволяют
    добавляет индекс к названию (sheet_name + index) и создает еще один лист с названием
    sheet_name + (index + 1)"""
    # TODO: доделать логику добавления данных с учетом лимитов
    data = [] if data is None else data
    if not end_row and len(data) == 0:
        print(f'[add_spreadsheet_data] incoming data is empty: {data}')
        return
    if len(header) == 0:
        print(f'[add_spreadsheet_data] invalid header: {header}')
        return
    if limit_per_sheet > 400000:
        limit_per_sheet = 400000
    if chunk_size > 40000:
        chunk_size = 40000
    if service is None:
        service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    sheet = None
    sheet_id = None
    for sheet_ in sheets:
        if sheet_.get('properties').get('title') == sheet_name:
            sheet = sheet_
            sheet_id = sheet_.get('properties').get('sheetId')
    row_limit = sheet.get('properties').get('gridProperties').get('rowCount')
    col_limit = sheet.get('properties').get('gridProperties').get('columnCount')
    if col_limit > len(header):
        resize_sheet(spreadsheet_id, sheet_id, row_limit, len(header))
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name + '!' + 'A1:B',
        majorDimension='ROWS'
    ).execute()
    rows = values.get('values')
    count = len(rows) if rows else 0
    if rows and '[INFO]' in rows[len(rows) - 1][0]:
        delete_dimension(spreadsheet_id, sheet_id, count - 1, count, service)
        count -= 1
        row_limit -= 1
    if count == 0:
        data.insert(0, header)
        set_row_color(spreadsheet_id, sheet_id, 0, 1, len(header))
    if end_row and (len(data) == 0 or '[INFO]' not in str(data[len(data) - 1][0])):
        data.append(['[INFO] ' + end_row])
    data_ = None
    if limit_per_sheet < count + len(data):
        data_ = data[limit_per_sheet - count:]
        data = data[0:limit_per_sheet - count]
    if row_limit < count + len(data):
        expand = count + len(data) - row_limit
        append_dimension(spreadsheet_id, sheet_id, row_limit - 1, expand, 21, service)
    if end_row and not data_:
        set_row_color(spreadsheet_id, sheet_id, len(data) + count - 1, len(data) + count, len(header))
    set_row_size(spreadsheet_id, sheet_id, 1, count + len(data), 21)
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        range_ = get_range([1, count + 1], [len(header), len(chunk) + count + 1])
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": sheet_name + '!' + range_,
                     "majorDimension": 'ROWS',
                     "values": chunk},
                ]
            }
        ).execute()
        count += len(chunk)
    if data_:
        print('[add_spreadsheet_data] add new sheet')
        add_sheet(spreadsheet_id, len(header), service)
        add_spreadsheet_data(data_, spreadsheet_id, header, limit_per_sheet, chunk_size, service, end_row)


def get_table_indexes_google(spreadsheet_id, service=None):
    if service is None:
        service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    sheet = sheets[0]
    sheet_name = sheet.get('properties').get('title')
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name + '!' + 'A2:B',
        majorDimension='ROWS'
    ).execute()
    rows = values.get('values')
    first = int(rows[0][0]) if rows and len(rows) > 0 else None
    sheet = sheets[-1]
    sheet_name = sheet.get('properties').get('title')
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name + '!' + 'A2:B',
        majorDimension='ROWS'
    ).execute()
    rows = values.get('values')
    if rows and '[INFO]' in rows[len(rows) - 1][0]:
        rows = rows[0:-1]
    last = int(rows[len(rows) - 1][0]) if rows and len(rows) > 0 else None
    print(f'first: {first}, last: {last} (google)')
    return first, last


def clear_spreadsheet(spreadsheet_id, col_count=26, service=None):
    """Полностью очищает таблицу удаляя все листы, оставляет только 1 пустой лист с названием Лист 1"""
    if service is None:
        service = get_service()
    insert_sheet(spreadsheet_id, col_count, service)
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    for i, sheet in enumerate(reversed(sheets)):
        if i < len(sheets) - 1:
            sheet_id = sheet.get('properties').get('sheetId')
            delete_sheet(spreadsheet_id, sheet_id, service)


def replace_sheet(spreadsheet_id, sheet_name, col_count=26, service=None):
    """Заменяет лист с назавнием sheet_name на новый пустой лист с такимже названием"""
    if service is None:
        service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    insert_id = 0
    insert_index = 0
    del_id = 0
    check = []
    for sheet in sheets:
        sheet_id = sheet.get('properties').get('sheetId')
        check.append(sheet_id)
        while insert_id in check:
            insert_id += 1
        if sheet.get('properties').get('title') == sheet_name:
            del_id = sheet_id
            insert_index = sheet.get('properties').get('index') + 1

    requests = []
    # rename sheet for delete
    prop = {
        'updateSheetProperties': {
            'properties': {
                'sheetId': del_id,
                'title': sheet_name + ' (temp)'
            },
            "fields": "title"
        }
    }
    requests.append(prop)
    # insert sheet
    requests.append({
        'addSheet': {
            'properties': {
                'title': sheet_name,
                'sheetType': 'GRID',
                'sheetId': insert_id,
                'index': insert_index,
                'gridProperties': {'rowCount': 1000, 'columnCount': col_count},
                'tabColor': {
                    'red': 0.44,
                    'green': 0.99,
                    'blue': 0.50
                }
            }
        }
    })
    # del sheet
    prop = {
        "deleteSheet": {
            "sheetId": del_id
        }
    }
    requests.append(prop)
    request_body = {'requests': requests}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()


def check_header(spreadsheet_id, header, service=None):
    if service is None:
        service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    range_ = get_range([1, 1], [len(header), 2])
    for sheet in sheets:
        sheet_name = sheet.get('properties').get('title')
        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name + '!' + range_,
            majorDimension='ROWS'
        ).execute()
        rows = values.get('values')
        if rows and rows[0] != header:
            return False
    return True


def get_spreadsheet_rows(spreadsheet_id, header, service=None, revers: bool = False):
    if service is None:
        service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets')
    range_ = get_range([1, 2], [len(header), None])
    iter_sheets = sheets if not revers else reversed(sheets)
    for sheet in iter_sheets:
        sheet_name = sheet.get('properties').get('title')
        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name + '!' + range_,
            majorDimension='ROWS'
        ).execute()
        rows = values.get('values')
        if rows:
            if '[INFO]' in rows[-1][0]:
                rows = rows[0:-1]
            iter_rows = rows if not revers else reversed(rows)
            for row in iter_rows:
                yield row
