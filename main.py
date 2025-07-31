from flask import Flask, request, jsonify
from firstrade import FirstradeAutoTrader

app = Flask(__name__)

@app.route("/", methods=["GET"])
def run_trade():
    # 取得 URL 查詢參數
    symbol = request.args.get("symbol", default="VT").upper()
    amount = request.args.get("amount", default="5")

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400

    # 登入與下單
    try:
        trader = FirstradeAutoTrader(username="XXXXX", password="XXXXX")
        trader.login()
        trader.fetch_accounts()
        result = trader.place_order(symbol=symbol, amount=amount)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
