from tinkoff.invest import Client
from tinkoff.invest.exceptions import RequestError
import mydata


with Client(mydata.TOKEN) as client:
    try:
        result = client.market_data.get_order_book(instrument_id=mydata.UID_SBER, depth=3)
        
        print('Глубина стакана:', result.depth)
        print('Множество пар значений на продажу:', result.asks)
        print('UID идентификатор инструмента:', result.instrument_uid)
        
        how_have_liquidity = 0
        for i in result.asks:
            how_have_liquidity += i.quantity
        print('liquidity:', how_have_liquidity)
        
    except RequestError as e:
        print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)
    
    

    
    