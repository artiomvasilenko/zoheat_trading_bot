'''
https://tinkoff.github.io/investAPI/head-stoporders/
'''

from tinkoff.invest import Client
from tinkoff.invest.exceptions import RequestError
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation
from decimal import Decimal
import mydata

def post_take_profit():

    with Client(mydata.TOKEN) as client:
        
        # получение последней стоимости инструмента
        last_price = decimal_to_quotation(Decimal(271.29))
        print(f"last price = {last_price}")
        last_price = quotation_to_decimal(last_price)
        print(f"last price = {last_price}")

        # расчёт цены с тп
        calculated_price = last_price + last_price * Decimal(mydata.TAKEPROFIT / 100)
        print(f"calculated_price = {calculated_price}")
        
        
        # получение минимального шага цены
        min_price_increment = client.instruments.get_instrument_by(
            id_type=3,
            id=mydata.UID_SBER
            ).instrument.min_price_increment
        print(f'min_price_increment: {min_price_increment}')
        number_digits_after_point = 9 - len(str(min_price_increment.nano)) + 1
        print(f'number_digits_after_point: {number_digits_after_point}')
        min_price_increment = quotation_to_decimal(min_price_increment)
        print(f'min_price_increment: {min_price_increment}')
        
        # расчет цены для инструмента, которая равна 
        # кратному минимальному шагу цены
        calculated_price = (
            round(calculated_price / min_price_increment) * min_price_increment
        )
        print(f"calculated_price = {calculated_price}")
        
        
        
        try:
            tp_result = client.stop_orders.post_stop_order(
                instrument_id=mydata.UID_SBER,
                quantity=mydata.QUANTITY,
                price=decimal_to_quotation(Decimal(calculated_price)),
                stop_price=decimal_to_quotation(Decimal(calculated_price)),
                direction=2, # 1-buy, 2-sell
                account_id=mydata.ACCOUNT_ID,
                stop_order_type=1,      # 1-tp, 2-sl, 3-sl
                expiration_type=1,  # 1-до отмены, 2-до даты
                )
            print(tp_result)
        
        except RequestError as e:
            print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)
        
        
def post_stop_loss():

    with Client(mydata.TOKEN) as client:
        
        # получение последней стоимости инструмента
        last_price = decimal_to_quotation(Decimal(271.29))
        print(f"last price = {last_price}")
        last_price = quotation_to_decimal(last_price)
        print(f"last price = {last_price}")

        # расчёт цены с тп
        calculated_price = last_price - last_price * Decimal(mydata.STOPLOSS / 100)
        print(f"calculated_price = {calculated_price}")
        
        
        # получение минимального шага цены
        min_price_increment = client.instruments.get_instrument_by(
            id_type=3,
            id=mydata.UID_SBER
            ).instrument.min_price_increment
        print(f'min_price_increment: {min_price_increment}')
        number_digits_after_point = 9 - len(str(min_price_increment.nano)) + 1
        print(f'number_digits_after_point: {number_digits_after_point}')
        min_price_increment = quotation_to_decimal(min_price_increment)
        print(f'min_price_increment: {min_price_increment}')
        
        # расчет цены для инструмента, которая равна 
        # кратному минимальному шагу цены
        calculated_price = (
            round(calculated_price / min_price_increment) * min_price_increment
        )
        print(f"calculated_price = {calculated_price}")
        
        
        
        try:
            tp_result = client.stop_orders.post_stop_order(
                instrument_id=mydata.UID_SBER,
                quantity=mydata.QUANTITY,
                price=decimal_to_quotation(Decimal(calculated_price)),
                stop_price=decimal_to_quotation(Decimal(calculated_price)),
                direction=2, # 1-buy, 2-sell
                account_id=mydata.ACCOUNT_ID,
                stop_order_type=2,      # 1-tp, 2-sl, 3-slimit
                expiration_type=1,  # 1-до отмены, 2-до даты
                )
            print(tp_result)
        
        except RequestError as e:
            print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)
        



if __name__ == '__main__':
    post_take_profit()
    post_stop_loss()
    
