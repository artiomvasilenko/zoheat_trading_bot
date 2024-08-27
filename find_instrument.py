from tinkoff.invest import Client
import mydata
        
def find_instrument(query):
    with Client(mydata.TOKEN) as client:
        result = client.instruments.find_instrument(query=query, api_trade_available_flag=True, instrument_kind=2)
        
        if result.instruments != [] and result.instruments[0].for_qual_investor_flag == False:            
            status = client.market_data.get_trading_status(instrument_id=result.instruments[0].uid)
            if status.trading_status == 5:
                return result.instruments[0]
            else:
                print(mydata.security_trading_status[status.trading_status], end='\n\n')
                return None
        else:
            return None
        
if __name__ == "__main__":
    print('instrument find_instrument')