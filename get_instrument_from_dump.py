import pickle

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
        

with open('dump.pickle', 'rb') as file:
    all_tickers_rus = pickle.load(file)

def get_instrument_isin(name_ticker):
    if name_ticker in all_tickers_rus:
        return all_tickers_rus[name_ticker].isin
    else:
        return None

if __name__ == '__main__':    
    print(get_instrument_isin('SBER'))