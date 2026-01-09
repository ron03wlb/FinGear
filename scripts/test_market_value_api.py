from FinMind.data import DataLoader
import pandas as pd
from datetime import datetime, timedelta

dl = DataLoader()
# No login needed for public dataset tests usually, or use token
# dl.login_by_token(api_token="...") 

end_date = datetime.now()
start_date = end_date - timedelta(days=30)
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

print(f"Testing 2330 from {start_str} to {end_str}")
try:
    df = dl.taiwan_stock_market_value(
        stock_id='2330',
        start_date=start_str,
        end_date=end_str
    )
    print(f"Result for 2330:\n{df}")
except Exception as e:
    print(f"Failed for 2330: {e}")

print("\nTesting batch [2330, 2317]")
try:
    df = dl.taiwan_stock_market_value(
        stock_id_list=['2330', '2317'],
        start_date=start_str,
        end_date=end_str
    )
    print(f"Result for batch:\n{df}")
except Exception as e:
    print(f"Failed for batch: {e}")
