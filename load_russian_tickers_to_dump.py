import pickle
from tinkoff.invest import (
    Client,
    )
from tinkoff.invest.services import InstrumentsService
from mydata import TOKEN
ticker = 'SBER'
all_tickers_rus = {}

class Instrument:
    def __init__(
        self,
        ticker,
        name,
        country_of_risk,
        country_of_risk_name,
        currency,
        lot,
        figi,
        isin,
        uid,
        buy_available_flag,
        sell_available_flag,
        for_qual_investor_flag,
    ):
        self.ticker = ticker
        self.name = name
        self.country_of_risk = country_of_risk
        self.country_of_risk_name = country_of_risk_name
        self.currency = currency
        self.lot = lot
        self.figi = figi
        self.isin = isin
        self.uid = uid
        self.buy_available_flag = buy_available_flag
        self.sell_available_flag = sell_available_flag
        self.for_qual_investor_flag = for_qual_investor_flag
        
        


with Client(TOKEN) as client:
    instruments: InstrumentsService = client.instruments
    result = getattr(instruments, 'shares')().instruments

    for i in result:
        if i.currency == 'rub' and i.country_of_risk == 'RU' and i.for_qual_investor_flag == False:
            all_tickers_rus[i.ticker] = Instrument(
                ticker=i.ticker,                                # MRKY
                name=i.name,                                    # МРСК Юга
                country_of_risk=i.country_of_risk,              # RU
                country_of_risk_name=i.country_of_risk_name,    # Российская Федерация
                currency=i.currency,                            # rub
                lot=i.lot,                                      # 10000
                figi=i.figi,                                    # BBG000C7P5M7
                isin=i.isin,                                    # RU000A0JPPG8
                uid=i.uid,                                      # c41a8e78-e4ee-4aa1-869a-9eff103b260a
                buy_available_flag=i.buy_available_flag,        # True
                sell_available_flag=i.sell_available_flag,      # True
                for_qual_investor_flag=i.for_qual_investor_flag # False
            )
            print(all_tickers_rus[i.ticker].name)
    
with open('dump.pickle', 'wb') as file:
    pickle.dump(all_tickers_rus, file)
        