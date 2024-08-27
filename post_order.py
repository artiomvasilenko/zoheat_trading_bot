from tinkoff.invest import Client
from tinkoff.invest.exceptions import RequestError
import uuid
import mydata


with Client(mydata.TOKEN) as client:
    try:
        order_id = client.orders.post_order(
            instrument_id=mydata.UID_SBER,
            quantity=mydata.QUANTITY,       # кол-во лотов
            direction=1,                     # 1 - покупка, 2 - продажа
            account_id=mydata.ACCOUNT_ID,
            order_type=2,       # 1 - limit, 2 - market, 3 - bestprice
            order_id=uuid.uuid4().hex
            )
        print('Биржевой идентификатор заявки:', order_id.order_id)
        print('Текущий статус заявки:', order_id.execution_report_status)
        print('Запрошено лотов:', order_id.lots_requested)
        print('Исполнено лотов:', order_id.lots_executed)
        print('Исполненная средняя цена одного инструмента в заявке:', order_id.executed_order_price)
        print('Итоговая стоимость заявки, включающая все комиссии:', order_id.total_order_amount)
        print('Фактическая комиссия по итогам исполнения заявки:', order_id.executed_commission)
        print('Дополнительные данные об исполнении заявки:', order_id.message)
        print('UID идентификатор инструмента:', order_id.instrument_uid)
    except RequestError as e:
        print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)
    
    

    
    