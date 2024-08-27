def get_instrument_id_figi_from_ticker_name(ticker):
    """tiker = VTBR
        tiker = SBER
        and other...
    """
    with Client(TOKEN) as client:
        instruments: InstrumentsService = client.instruments
        tickers = []
        for method in ["shares", "bonds", "etfs", "currencies", "futures"]:
            for item in getattr(instruments, method)().instruments:
                tickers.append(
                    {
                        "name": item.name,
                        "ticker": item.ticker,
                        "class_code": item.class_code,
                        "figi": item.figi,
                        "uid": item.uid,
                        "type": method,
                        "min_price_increment": quotation_to_decimal(
                            item.min_price_increment
                        ),
                        "scale": 9 - len(str(item.min_price_increment.nano)) + 1,
                        "lot": item.lot,
                        "trading_status": str(
                            SecurityTradingStatus(item.trading_status).name
                        ),
                        "api_trade_available_flag": item.api_trade_available_flag,
                        "currency": item.currency,
                        "exchange": item.exchange,
                        "buy_available_flag": item.buy_available_flag,
                        "sell_available_flag": item.sell_available_flag,
                        "short_enabled_flag": item.short_enabled_flag,
                        "klong": quotation_to_decimal(item.klong),
                        "kshort": quotation_to_decimal(item.kshort),
                    }
                )

        tickers_df = DataFrame(tickers)

        ticker_df = tickers_df[tickers_df["ticker"] == ticker]
        if ticker_df.empty:
            logger.error("Такого тикера не существует: %s", ticker)
            return

        figi = ticker_df["figi"].iloc[0]
        print(f"\nТикер {ticker} имеет ИД={figi}\n")
        print(f"Дополнительная информация для этого {ticker}:")
        print(ticker_df.iloc[0])
        return figi
    
if __name__ == '__main__':
    from tinkoff.invest import (
    Client,
    SecurityTradingStatus,
    )
    from tinkoff.invest.services import InstrumentsService
    from tinkoff.invest.utils import quotation_to_decimal
    from pandas import DataFrame
    
    
    print(get_instrument_id_figi_from_ticker_name('SBER'))