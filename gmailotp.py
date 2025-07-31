import base64
import re
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import time

# Gmail API 權限
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_mail_creds():
    creds = None
    # 嘗試載入本地憑證
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

            if creds and creds.expired:
                if creds.refresh_token:
                    try:
                        print("Access token 過期，正在刷新...")
                        creds.refresh(Request())
                        print("Refresh 成功，使用新的 access token")

                        # 更新 token.json
                        with open('token.json', 'w') as token:
                            token.write(creds.to_json())
                    except RefreshError as e:
                        print("Refresh token 無效或已撤銷，需重新登入")
                        creds = None  # 清除憑證
                else:
                    print("沒有 refresh token，需要重新登入")
                    creds = None
        except (json.JSONDecodeError, ValueError) as e:
            print("無法讀取 token.json，檔案可能已損壞，將重新登入")
            creds = None
        except Exception as e:
            print(f"載入 token.json 發生錯誤：{e}")
            creds = None

    # 若尚未登入或 refresh 失敗 → 啟動授權流程
    if not creds or not creds.valid:
        try:
            print("啟動 OAuth 授權流程...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            print("授權成功，儲存 token.json")

            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"授權流程失敗：{e}")
            return None

    return creds


def get_ft_code(since_timestamp):
    creds = get_mail_creds()
    service = build('gmail', 'v1', credentials=creds)

    query = 'from:service@firstrade.com'
    timeout = 60  # 最多等待 30 秒，可自行調整
    poll_interval = 5  # 每 2 秒查一次
    start_time = time.time()

    while time.time() - start_time < timeout:
        results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
        messages = results.get('messages', [])

        for msg in messages:
            msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
            internal_ts = int(msg_detail.get('internalDate', '0'))
            if internal_ts >= since_timestamp:
                payload = msg_detail.get('payload', {})
                parts = payload.get('parts', [])
                content = ''
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        body = part.get('body', {}).get('data', '')
                        content = base64.urlsafe_b64decode(body).decode('utf-8')
                        break
                else:
                    content = msg_detail.get('snippet', '')

                codes = re.findall(r'\*(\d{6})\*', content)
                if codes:
                    print(f"找到驗證碼：{codes[0]}")
                    return codes[0]
        print("=========")
        time.sleep(poll_interval)

    print("超時，未取得新驗證碼")
    return None
