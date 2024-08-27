'''
Алгоритм:
1. Выставляем рыночный ордер по бумаге на всю котлету
2. Если он не исполнен, то возвращаем ошибку
3. Если он исполнен и вернулся его идентификатор, то
4. Выставляем ТП на цену +2% к цене покупки
5. Выставляем СЛ на цену -1% от цену покупки
6. Замораживаем до 16:00 по Москве сделку, в 16:00 закрываем её с любым результатом
'''

from tinkoff.invest import (
    Client,
    OrderDirection,
    OrderExecutionReportStatus,
    OrderType,
    PostOrderResponse,
    StopOrderDirection,
    StopOrderExpirationType,
    StopOrderType,
    SecurityTradingStatus,
    )
from tinkoff.invest.services import Services, InstrumentsService
from tinkoff.invest.utils import decimal_to_quotation, money_to_decimal, now, quotation_to_decimal
from datetime import timedelta
from decimal import Decimal
from pandas import DataFrame
import mydata
import logging
import os
import uuid
import pickle


TOKEN = mydata.TOKEN
logging.basicConfig(filename='logger.log', 
                    level=logging.INFO, 
                    format='%(asctime)s - %(message)s', 
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
QUANTITY = 1
# INSTRUMENT_ID = "BBG001M2SC01"
TAKE_PROFIT_PERCENTAGE = 0.02
STOP_LOSS_PERCENTAGE = -0.01
MIN_PRICE_STEP = 0.02
STOP_ORDER_EXPIRE_DURATION = timedelta(hours=1)
EXPIRATION_TYPE = StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_DATE
tiker_name = 'SBER'


def cancel_all_order():
    with Client(TOKEN) as client:
        response = client.users.get_accounts()
        account, *_ = response.accounts
        account_id = account.id
        logger.info("Orders: %s", client.orders.get_orders(account_id=account_id))
        client.cancel_all_orders(account_id=account.id)
        logger.info("Orders: %s", client.orders.get_orders(account_id=account_id))
            
def post_stop_orders(
    client: Services, account_id: str, post_order_response: PostOrderResponse, instrument_id):
    executed_order_price = money_to_decimal(post_order_response.executed_order_price)
    take_profit_price = executed_order_price * Decimal((1 + TAKE_PROFIT_PERCENTAGE))
    take_profit_price -= take_profit_price % Decimal(MIN_PRICE_STEP)
    take_profit_response = client.stop_orders.post_stop_order(
        quantity=QUANTITY,
        price=decimal_to_quotation(take_profit_price),
        stop_price=decimal_to_quotation(take_profit_price),
        direction=StopOrderDirection.STOP_ORDER_DIRECTION_SELL,
        account_id=account_id,
        stop_order_type=StopOrderType.STOP_ORDER_TYPE_TAKE_PROFIT,
        instrument_id=instrument_id,
        expire_date=now() + STOP_ORDER_EXPIRE_DURATION,
        expiration_type=EXPIRATION_TYPE,
    )
    logger.info(
        "Ордер Take Profit размещен stop_order_id=%s. Цена: %s",
        take_profit_response.stop_order_id,
        take_profit_price,
    )
    print(
        "Ордер Take Profit размещен stop_order_id=%s. Цена: %s",
        take_profit_response.stop_order_id,
        take_profit_price,
    )
    stop_loss_price = executed_order_price * Decimal((1 + STOP_LOSS_PERCENTAGE))
    stop_loss_price -= stop_loss_price % Decimal(MIN_PRICE_STEP)
    take_profit_response = client.stop_orders.post_stop_order(
        quantity=QUANTITY,
        stop_price=decimal_to_quotation(stop_loss_price),
        direction=StopOrderDirection.STOP_ORDER_DIRECTION_SELL,
        account_id=account_id,
        stop_order_type=StopOrderType.STOP_ORDER_TYPE_STOP_LOSS,
        instrument_id=instrument_id,
        expire_date=now() + STOP_ORDER_EXPIRE_DURATION,
        expiration_type=EXPIRATION_TYPE,
    )
    logger.info(
        "Ордер Stop loss был размещен stop_order_id=%s. Цена: %s",
        take_profit_response.stop_order_id,
        stop_loss_price,
    )
    print(
        "Ордер Stop loss был размещен stop_order_id=%s. Цена: %s",
        take_profit_response.stop_order_id,
        stop_loss_price,
    )

def create_order_with_instrument(instrument_id):
    with Client(TOKEN) as client:
        response = client.users.get_accounts()
        account, *_ = response.accounts
        account_id = account.id

        order_id = uuid.uuid4().hex

        logger.info("Create order with %s instrument %s, order_id=%s", QUANTITY, instrument_id, order_id)
        print(f'Размещение заявки количеством {QUANTITY} инструмента {instrument_id}, с order_id={order_id}')
        post_order_response: PostOrderResponse = client.orders.post_order(
            quantity=QUANTITY,
            direction=OrderDirection.ORDER_DIRECTION_BUY,
            account_id=account_id,
            order_type=OrderType.ORDER_TYPE_MARKET,
            order_id=order_id,
        )

        status = post_order_response.execution_report_status
        if status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL:
            logger.info("Ордер успешно размещен, выставление стоп ордера...")
            print("Ордер успешно размещен, выставление стоп ордера...")

            post_stop_orders(
                client=client,
                account_id=account_id,
                post_order_response=post_order_response,
                instrument_id=instrument_id
            )
        else:
            logger.info(
                'Ордер не размещен: (%s) "%s"',
                post_order_response.execution_report_status,
                post_order_response.message,
            )
            logger.info("Отмена всех ордеров")
            print(
                'Ордер не размещен: (%s) "%s"',
                post_order_response.execution_report_status,
                post_order_response.message,
            )
            print("Отмена всех ордеров")
            client.cancel_all_orders(account_id=account_id)      



def main():
    logger.info('Started')
    
   
    
    logger.info('Finished')

if __name__ == '__main__':
    main()