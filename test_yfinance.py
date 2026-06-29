import json
import yfinance as yf

try:
    ticker = yf.Ticker('ORACLE')
    info = ticker.info
    result = {'status': 'success', 'info': info}
except Exception as e:
    result = {'status': 'error', 'message': str(e)}

with open('yfinance_out.json', 'w') as f:
    json.dump(result, f, indent=2)
