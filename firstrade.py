import requests
import time
from gmailotp import get_ft_code

class FirstradeAutoTrader:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.sid = None
        self.ftat = None
        self.account_numbers = []
        self.account_balances = {}

        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "access-token": "833w3XuIFycv18ybi",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "host": "api3x.firstrade.com",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }

    def login(self):
        # 第一步：登入帳號密碼
        data = {"username": self.username, "password": self.password}
        res = self.session.post("https://api3x.firstrade.com/sess/login", data=data, headers=self.headers)
        res.raise_for_status()
        login_json = res.json()

        t_token = login_json.get("t_token")
        otp_options = login_json.get("otp")
        recipientId = next((item["recipientId"] for item in otp_options if item["channel"] == "email"), None)
        if not recipientId:
            raise ValueError("未找到 email otp 選項")

        # 第二步：寄驗證碼
        send_time_ms = int(time.time() * 1000) - 10000
        res = self.session.post("https://api3x.firstrade.com/sess/request_code",
                                data={"recipientId": recipientId, "t_token": t_token},
                                headers=self.headers)
        res.raise_for_status()
        mfa_json = res.json()
        verificationSid = mfa_json.get("verificationSid")

        # 第三步：取驗證碼並驗證
        mfa_code = get_ft_code(since_timestamp=send_time_ms)
        data = {
            "otpCode": mfa_code,
            "verificationSid": verificationSid,
            "remember_for": "30",
            "t_token": t_token,
        }

        verify_headers = self.headers.copy()
        verify_headers["sid"] = verificationSid
        res = self.session.post("https://api3x.firstrade.com/sess/verify_pin", data=data, headers=verify_headers)
        res.raise_for_status()

        verify_json = res.json()
        self.sid = verify_json.get("sid")
        self.ftat = verify_json.get("ftat")

    def fetch_accounts(self):
        headers = {
            "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "access-token": "833w3XuIFycv18ybi",
            "cache-control": "max-age=0",
            "host": "api3x.firstrade.com",
            "sid": self.sid,
            "ftat": self.ftat,
            "user-agent": self.headers["user-agent"]
        }

        res = self.session.get("https://api3x.firstrade.com/private/acct_list", headers=headers)
        res.raise_for_status()
        all_accounts = res.json()

        for item in all_accounts.get("items", []):
            acc = item["account"]
            self.account_numbers.append(acc)
            self.account_balances[acc] = item["total_value"]

    def place_order(self, symbol="VT", amount=100):
        if not self.account_numbers:
            raise RuntimeError("尚未登入或取得帳戶")

        data = {
            "account": self.account_numbers[0],
            "symbol": symbol,
            "transaction": "B",
            "dollar_amount": amount,
            "duration": "0",  # Day
            "preview": "false",
            "instructions": "0",
            "price_type": "1",  # Market
            "limit_price": "0",
        }

        headers = {
            "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "access-token": "833w3XuIFycv18ybi",
            "cache-control": "max-age=0",
            "host": "api3x.firstrade.com",
            "sid": self.sid,
            "ftat": self.ftat,
            "user-agent": self.headers["user-agent"]
        }

        res = self.session.post("https://api3x.firstrade.com/private/stock_order", data=data, headers=headers)
        res.raise_for_status()
        return res.json()
