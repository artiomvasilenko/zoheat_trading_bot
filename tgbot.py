
from telegram import (
    Update, 
    ReplyKeyboardRemove, 
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    )
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    ApplicationBuilder,
    ContextTypes,
    filters,
    ConversationHandler,
    )
from peewee import *
from tinkoff.invest import Client
import uuid
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation
from decimal import Decimal
from datetime import date
from math import ceil, floor
from api_key_tg import token
import json

# Текущий статус заявки (поручения)
execution_report_status = {
    0: None,
    1: 'Исполнена',
    2: 'Отклонена',
    3: 'Отменена пользователем',
    4: 'Новая',
    5: 'Частично исполнена',
}
security_trading_status = {
    0: 'Торговый статус не определён',
    1: 'Недоступен для торгов',
    2: 'Период открытия торгов',
    3: 'Период закрытия торгов',
    4: 'Перерыв в торговле',
    5: 'Нормальная торговля',
    6: 'Аукцион закрытия',
    7: 'Аукцион крупных пакетов',
    8: 'Дискретный аукцион',
    9: 'Аукцион открытия',
    10: 'Период торгов по цене аукциона закрытия',
    11: 'Сессия назначена',
    12: 'Сессия закрыта',
    13: 'Сессия открыта',
    14: 'Доступна торговля в режиме внутренней ликвидности брокера',
    15: 'Перерыв торговли в режиме внутренней ликвидности брокера',
    16: 'Недоступна торговля в режиме внутренней ликвидности брокера',
}


db = SqliteDatabase('tdata.db')
class Tinkoff_invest_tokens(Model):
        user_id = IntegerField(unique=True)
        token = CharField()
        sl = IntegerField()
        tp = IntegerField()
        account = CharField(null=True)
        
        class Meta:
            database = db
            
class Trades(Model):
    user_id = IntegerField()
    order_id = CharField()
    date = DateField()
    instrument_uid = CharField()
    instrument_name = CharField()
    instrument_short_name = CharField()
    lot = IntegerField()
    price = FloatField()
    status = BooleanField(default=True) # True if open, False if close
    price_on_close = FloatField(null=True)
    date_on_close = DateField(null=True)
    result = FloatField(null=True)   # Процент закрытия
    
    class Meta:
            database = db
    

def connect_db():
    db.connect()     
    db.create_tables([Tinkoff_invest_tokens, Trades])

Q1_TOKEN, Q2_SL, Q3_TP = range(3)
CHANGE_TOKEN, CHANGE_SL, CHANGE_TP = [range(1),] * 3

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if check_token_in_base(update.message.from_user.id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f'Привет, {update.message.chat.first_name}. '
                    'Отправь мне тикер в формате "SBER" без кавычек'
            )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text='Привет! Я не нашёл тебя в базе данных.'
                'Давай пройдем короткий опрос. '
                'Для начала отправь мне API ключ Тинькофф Инвестиций.'
            )
        return Q1_TOKEN
    
def find_instrument(query, token):
    '''Ищет инстументы по тикеру
    Возвращает объект с инструментами либо пустой массив [] если ничего не найдено
    '''
    with Client(token) as client:
        return client.instruments.find_instrument(query=query, api_trade_available_flag=True, instrument_kind=2) 

# Обработчик текстовых сообщений
async def text_from_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.message.from_user.id
    user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
    
    if check_token_in_base(update.message.from_user.id):
        instruments = find_instrument(user_message.upper(), user.token)
        if instruments.instruments == []:
            await update.message.reply_text(f'По запросу "{user_message}" ничего не найдено.')
        elif len(instruments.instruments) > 20:
            keyboard = [[InlineKeyboardButton(f'{ins.name}', callback_data='text_from_user' + ins.uid)] for ins in instruments.instruments[:20]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f'Найдено слишком много бумаг: {len(instruments.instruments)}.\nОтображены первые 20 инструментов.\nВыбери по каком выставлять ордер либо уточни запрос.',
                reply_markup=reply_markup)  
        else:
            keyboard = [[InlineKeyboardButton(f'{ins.name}', callback_data='text_from_user' + ins.uid)] for ins in instruments.instruments]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('По запросу найдены следующие акции. Выбери каким торговать: ', reply_markup=reply_markup)
    else:
        await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text='Привет! Я не нашёл тебя в базе данных. '
                        'Для начала отправь команду /start'
                    )



async def delete_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''Удаление клавиатуры, которая была создана случайно
    Наверное в будущем эта функция не понадобится, но пока оставим'''
    await update.message.reply_text(
        "Deleted",
        reply_markup=ReplyKeyboardRemove(),
    )

async def save_choosed_account_to_bd(user_id, account_id):
    user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
    user.account = account_id
    user.save()
    
def get_accounts(token):
    '''Запрашивает все аккаунты и возвращает объект со всеми аккаунтами вида:
    GetAccountsResponse(
        accounts=[
            Account(
                id='2149870830', 
                type=<AccountType.ACCOUNT_TYPE_TINKOFF: 1>, 
                name='Основной брокерский счёт', 
                status=<AccountStatus.ACCOUNT_STATUS_OPEN: 2>, 
                opened_date=datetime.datetime(2022, 2, 10, 0, 0, tzinfo=datetime.timezone.utc), 
                closed_date=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc), 
                access_level=<AccessLevel.ACCOUNT_ACCESS_LEVEL_FULL_ACCESS: 1>
            )
        ]
    )    
    '''
    with Client(token) as client:
        result = client.users.get_accounts()
        return result
   
async def choose_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''Функция выбора аккаунта для торговли и занесение номера аккаунта в БД'''
    # проверяем, а есть ли пользователь вообще
    if check_token_in_base(update.message.from_user.id):
        user_id = update.message.from_user.id
        user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
        token = user.token
        accounts = get_accounts(token)
        # создание клавиатуры
        keyboard = [[
            InlineKeyboardButton(
                f'{acc.name} - {acc.id}', callback_data='choose_account_' + acc.id)] 
                    for acc in accounts.accounts if acc.access_level == 1
                    ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выбери аккаунт: ', reply_markup=reply_markup)
    else:
        await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text='Привет! Я не нашёл тебя в базе данных. '
                        'Для начала отправь команду /start'
                    )
def get_balance(token, account_id):
    '''функция запрашивает сколько денег в рублях есть у аккаунта'''
    with Client(token) as client:
        moneys = client.operations.get_positions(account_id=account_id).money
        for money in moneys:
            if money.currency == 'rub':
                return money.units

def get_price_one_lot(token, instrument_uid):
    '''функция запрашивает стоимость одного лота инструмента'''
    with Client(token) as client:
        # получаем кол-во акций в одном лоте
        lot = client.instruments.share_by(id_type=3,
                                          id=instrument_uid).instrument.lot
        # получение последней стоимости инструмента
        last_price = client.market_data.get_last_prices(
            instrument_id=[instrument_uid]).last_prices[0].price
        # перевод в decimal
        last_price = quotation_to_decimal(last_price)
        # перемножаем и округляем в большую сторону
        full_price = ceil(last_price * lot)
        # возвращаем полученный итог
        return full_price       
                
def split_by_percentage(num):
    # функция разбивает полученное число по процентам 10%, 25%, 50%, 75%, 100% и крайние значения в массиве []
    values = []
    percents = [10, 25, 50, 75, 100]
    result = 0
        
    if num < 5:
        for percent in range(num):
            values.append(percent + 1)
    elif num < 10:
        for percent in percents:
            calculate = floor((num * percent) / 100)
            if calculate == 0: calculate = 1
            if calculate == result: continue
            result = calculate
            if result > num: result = num
            values.append(result)
    elif num < 50:
        for percent in percents:
            calculate = floor(num * percent / 100 / 5) * 5
            if calculate == 0: calculate = 1
            if calculate == result: continue
            result = calculate
            if result > num: result = num
            values.append(result)
            if result > num - 5 and result != num: values.append(num)
    elif num < 500:
        for percent in percents:
            calculate = floor(num * percent / 100 / 10) * 10
            if calculate == 0: calculate = 1
            if calculate == result: continue
            result = calculate
            if result > num: result = num
            values.append(result)
            if result > num - 10 and result != num: values.append(num)
    else:
        for percent in percents:
            calculate = floor(num * percent / 100 / 100) * 100
            if calculate == 0: calculate = 1
            if calculate == result: continue
            result = calculate
            if result > num: result = num
            values.append(result)
            if result > num - 100 and result != num: values.append(num)
    
    return values

def check_trading_status(token, instrument_uid):
    '''Функция проверяет, позможна ли торговля. Возвращает статус торговли'''
    with Client(token) as client:
        return client.instruments.share_by(id_type=3, id=instrument_uid).instrument.trading_status
    
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''Функция обработки выбора кнопок'''
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('choose_account_'):
        data = query.data.replace('choose_account_', '')
        await save_choosed_account_to_bd(query.from_user.id, data)
        await query.edit_message_text(text=f'Аккаунт {data} сохранен!') 
         
    if query.data.startswith('text_from_user'):
        # собираю информацию
        user_id = query.from_user.id
        user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
        token = user.token
        instrument_uid = query.data.replace('text_from_user', '')
        # получим информацию по балансу аккаунта:
        balance = get_balance(token, user.account)
        price_one_lot = get_price_one_lot(token, instrument_uid)
        # рассчитываю сколько я могу купить лотов по моим бабулесам с округлением в меньшую сторону
        how_many_i_can_to_buy = floor(balance / price_one_lot)
        splited = split_by_percentage(how_many_i_can_to_buy)
        keyboard = [[InlineKeyboardButton(
            lot, 
            callback_data='lot' + json.dumps({'i': instrument_uid,
                                              'l': lot}))] for lot in splited]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
                text=f'Выбрано: "{query.message.reply_markup.inline_keyboard[0][0].text}"\n'
                    f'Доступно для покупки: {how_many_i_can_to_buy}\n'
                    'Каким количеством лотов зайти?',
                reply_markup=reply_markup
                )
        
    if query.data.startswith('lot'):
        # собираю информацию
        await query.edit_message_text(text=f'Проверяю информацию...')
        user_id = query.from_user.id
        user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
        token = user.token
        data = query.data.replace('lot', '')
        data = json.loads(data)
        instrument_uid = data['i']
        lot = data['l']
        # выставляем ордер
        status = check_trading_status(token, instrument_uid)
        if status in [5,]: # 5 - торги на бирже, 14 - торги Доступна торговля в режиме внутренней ликвидности брокера
            await query.edit_message_text(text=f'Выставляю ордер...')
            result = post_order(token=token, 
                                instrument_uid=instrument_uid, 
                                quantity=lot,
                                account_id=user.account,)
            if result.execution_report_status == 1:
                await query.edit_message_text(text=
                    f'ОРДЕР ВЫСТАВЛЕН!\n'
                    f'Биржевой идентификатор заявки: {result.order_id}\n'
                    f'Запрошено лотов: {result.lots_requested}\n'
                    f'Исполнено лотов: {result.lots_executed}\n'
                    f'Исполненная средняя цена одного инструмента в заявке: '
                        f'{round(quotation_to_decimal(result.executed_order_price), 2)} руб.\n'
                    f'Итоговая стоимость заявки: '
                        f'{round(quotation_to_decimal(result.total_order_amount))} руб.\n'
                    f'Текущий статус заявки: {execution_report_status[result.execution_report_status]}\n'
                    f'Дополнительные данные об исполнении заявки: {result.message}\n'
                    )
                sl = post_stop_loss(token, 
                                    instrument_uid,
                                    user.sl,
                                    lot,
                                    user.account)
                if sl['stop_order_id']:
                    await context.bot.send_message(
                        chat_id=update.callback_query.from_user.id,
                        text=f'Заявка Stop Loss успешно выставлена.\n'
                            f'Цена заявки Stop Loss: {round(sl["calculated_price"], 2)}\n'
                            f'Идентификатор заявки: {sl["stop_order_id"]}.'
                        )
                else:
                    await context.bot.send_message(
                        chat_id=update.callback_query.from_user.id,
                        text='При выставлении заявки произошла ошибка.'
                        )
                tp = post_take_profit(token, 
                                    instrument_uid,
                                    user.tp,
                                    lot,
                                    user.account)
                if tp['stop_order_id']:
                    await context.bot.send_message(
                        chat_id=update.callback_query.from_user.id,
                        text=f'Заявка Take Profit успешно выставлена.\n'
                            f'Цена заявки Take Profit: {round(tp["calculated_price"], 2)}\n'
                            f'Идентификатор заявки: {tp["stop_order_id"]}.'
                        )
                else:
                    await context.bot.send_message(
                        chat_id=update.callback_query.from_user.id,
                        text='При выставлении заявки произошла ошибка.'
                        )
                # записываем данные в БД
                await record_trade_to_db(
                    user_id = query.from_user.id, 
                    order_id = result.order_id, 
                    instrument_uid = result.instrument_uid, 
                    lot = result.lots_executed, 
                    price = quotation_to_decimal(result.executed_order_price),
                    token = token,
                ) 
            else:
                await query.edit_message_text(
                    text=f'ОРДЕР НЕ ВЫСТАВЛЕН'
                    f'Биржевой идентификатор заявки: {result.order_id}\n'
                    f'Текущий статус заявки: {result.execution_report_status}\n'
                    f'Дополнительные данные об исполнении заявки: {result.message}\n'
                    )
        else:
            await query.edit_message_text(
                    text=f'ОРДЕР НЕ ВЫСТАВЛЕН!\n'
                    f'Бумага не доступна для торговли.\n'
                    f'"{security_trading_status[status]}"')

async def record_trade_to_db(user_id, order_id, instrument_uid, lot, price, token):
    '''Функция записывает данные о сделке в базу данных'''
    instrument = find_instrument(instrument_uid, token)
    Trades.create(
        user_id = user_id,
        order_id = order_id,
        date = date.today(),
        instrument_uid = instrument_uid,
        instrument_name = instrument.instruments[0].name,
        instrument_short_name = instrument.instruments[0].ticker,
        lot = lot,
        price = price,
    )
    
            
def post_order(token, instrument_uid, quantity, account_id):
    '''
    Функция выставляет ордер.
    Принимает значения:
        token - для выставления ордера
        instrument_id - для выставления ордера согласно запросу
    Возвращает результат ордера
    '''
    with Client(token) as client:
        order = client.orders.post_order(
            instrument_id=instrument_uid,
            quantity=quantity,       # кол-во лотов
            direction=1,                     # 1 - покупка, 2 - продажа
            account_id=account_id,
            order_type=2,       # 1 - limit, 2 - market, 3 - bestprice
            order_id=uuid.uuid4().hex
            )
        return order
    
def post_stop_loss(token, instrument_uid, sl, quantity, account_id):
    '''
    Функция выставляет стоп лос по заявке
    Принимает значения:
        token - для выставления ордера
        instrument_id - для выставления ордера согласно запросу
        
    Возвращает результат заявки
    '''
    # получаем данные юзера из БД
    result = {}
    with Client(token) as client:
        # получение последней стоимости инструмента
        last_price = client.market_data.get_last_prices(
            instrument_id=[instrument_uid]).last_prices[0].price
        # перевод в decimal
        last_price = quotation_to_decimal(last_price)
        # расчёт цены с тп
        calculated_price = last_price - last_price * Decimal(sl / 100)
        result['calculated_price'] = calculated_price
        # получение минимального шага цены
        min_price_increment = client.instruments.get_instrument_by(
            id_type=3,
            id=instrument_uid
            ).instrument.min_price_increment
        # а вот ниже строка вообще не нужна похоже
        #number_digits_after_point = 9 - len(str(min_price_increment.nano)) + 1
        min_price_increment = quotation_to_decimal(min_price_increment)
        # расчет цены для инструмента, которая равна 
        # кратному минимальному шагу цены
        calculated_price = (
            round(calculated_price / min_price_increment) * min_price_increment
        )
        # выставляем ордер
        result['stop_order_id'] = client.stop_orders.post_stop_order(
            instrument_id=instrument_uid,
            quantity=quantity,
            price=decimal_to_quotation(Decimal(calculated_price)),
            stop_price=decimal_to_quotation(Decimal(calculated_price)),
            direction=2, # 1-buy, 2-sell
            account_id=account_id,
            stop_order_type=2,      # 1-tp, 2-sl, 3-slimit
            expiration_type=1,  # 1-до отмены, 2-до даты
            ).stop_order_id
        return result
    
def post_take_profit(token, instrument_uid, tp, quantity, account_id):
    '''
    Функция выставляет стоп лос по заявке
    Принимает значения:
        token - для выставления ордера
        instrument_id - для выставления ордера согласно запросу
        
    Возвращает результат заявки
    '''
    result = {}
    
    with Client(token) as client:
        # получение последней стоимости инструмента
        last_price = client.market_data.get_last_prices(
            instrument_id=[instrument_uid]).last_prices[0].price
        # перевод в decimal
        last_price = quotation_to_decimal(last_price)
        # расчёт цены с тп
        calculated_price = last_price + last_price * Decimal(tp / 100)
        result['calculated_price'] = calculated_price
        # получение минимального шага цены
        min_price_increment = client.instruments.get_instrument_by(
            id_type=3,
            id=instrument_uid
            ).instrument.min_price_increment
        # а вот ниже строка вообще не нужна похоже
        #number_digits_after_point = 9 - len(str(min_price_increment.nano)) + 1
        min_price_increment = quotation_to_decimal(min_price_increment)
        # расчет цены для инструмента, которая равна 
        # кратному минимальному шагу цены
        calculated_price = (
            round(calculated_price / min_price_increment) * min_price_increment
        )
        # выставляем ордер
        result['stop_order_id'] = client.stop_orders.post_stop_order(
            instrument_id=instrument_uid,
            quantity=quantity,
            price=decimal_to_quotation(Decimal(calculated_price)),
            stop_price=decimal_to_quotation(Decimal(calculated_price)),
            direction=2, # 1-buy, 2-sell
            account_id=account_id,
            stop_order_type=1,      # 1-tp, 2-sl, 3-slimit
            expiration_type=1,  # 1-до отмены, 2-до даты
            ).stop_order_id
        return result

           

# Обработчик ошибок
async def error(update: Update, context: CallbackContext):
    await context.bot.send_message(
                chat_id=update.callback_query.from_user.id, 
                text=f'ОШИБКА!\n{context.error}'
                )
    print(update, context.error)
    
def check_token_in_base(user_id):
    user = Tinkoff_invest_tokens.select().where(Tinkoff_invest_tokens.user_id == user_id)
    return True if user else False

async def q1_token(update: Update, context: CallbackContext):
    context.user_data['q1_token'] = update.message.text
    await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text='Какой Stop Loss устанавливать, в %? Напиши целое число.'
                )
    return Q2_SL

async def q2_sl(update: Update, context: CallbackContext):
    context.user_data['q2_sl'] = update.message.text
    await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text='Какой Take Profit устанавливать, в %? Напиши целое число.'
                )
    return Q3_TP

async def q3_tp(update: Update, context: CallbackContext):
    context.user_data['q3_tp'] = update.message.text
    user_id = update.message.from_user.id
    
    # запись в базу данных
    Tinkoff_invest_tokens().create(
        user_id=user_id, 
        token=context.user_data['q1_token'],
        sl=context.user_data['q2_sl'],
        tp=context.user_data['q3_tp'],
        )
    await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text='Всё успешно. Теперь выбери аккаунт с которого будем вести торговлю.\n'
                'Выбери команду /choose_account'
                )
    return ConversationHandler.END

# Отмена стартового опроса
async def start_cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Понимаешь, без этого робот работать не будет. Не бойся, это безопасно. Перезапусти вновь бот командой /start')
    return ConversationHandler.END

#функция смены токена
async def change_token(update: Update, context: CallbackContext):
    if check_token_in_base(update.message.from_user.id):
        await update.message.reply_text('Введи новый токен:')
        return CHANGE_TOKEN
    else:
        await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text='Привет! Я не нашёл тебя в базе данных. '
                        'Для начала отправь команду /start'
                    )

#функция смены стоп лосса
async def change_sl(update: Update, context: CallbackContext):
    if check_token_in_base(update.message.from_user.id):
        user_id = update.message.from_user.id
        data = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id).sl
        await update.message.reply_text(
            f'Текущий Stop Loss: {data}.\n'
            'Какой Stop Loss устанавливать, в %? Напиши целое число.')
        return CHANGE_SL
    else:
        await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text='Привет! Я не нашёл тебя в базе данных. '
                        'Для начала отправь команду /start'
                    )

#функция смены тэйк профита
async def change_tp(update: Update, context: CallbackContext):
    if check_token_in_base(update.message.from_user.id):
        user_id = update.message.from_user.id
        data = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id).tp
        await update.message.reply_text(
            f'Текущий Take Profit: {data}.\n'
            'Какой Take Profit устанавливать, в %? Напиши целое число.')
        return CHANGE_TP
    else:
        await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text='Привет! Я не нашёл тебя в базе данных. '
                        'Для начала отправь команду /start'
                    )

def check_number(number):
    try:
        float(number)
        return True
    except ValueError:
        return False

async def process_change_token(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    data = update.message.text
    user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
    user.token = data
    user.save()
    await update.message.reply_text(f'Токен {data} успешно сохранен!')
    return ConversationHandler.END
    
async def process_change_sl(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    data = update.message.text
    if check_number(data):
        user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
        user.sl = data
        user.save()
        await update.message.reply_text(f'Сохранено. Теперь будем выставлять Stop Loss {data}% от цены.')
        return ConversationHandler.END
    else:
        await update.message.reply_text(f'SL "{data}" не сохранён, так как не является числом. Повтори попытку')
        return CHANGE_SL
    
async def process_change_tp(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    data = update.message.text
    if check_number(data):
        user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
        user.tp = data
        user.save()
        await update.message.reply_text(f'Сохранено. Теперь будем выставлять Stop Loss {data}% от цены.')
        return ConversationHandler.END
    else:
        await update.message.reply_text(f'TP "{data}" не сохранён, так как не является числом. Повтори попытку')
        return CHANGE_TP

async def change_cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

async def delete_user(update: Update, context: CallbackContext):
    if check_token_in_base(update.message.from_user.id):
        user_id = update.message.from_user.id
        Tinkoff_invest_tokens.delete().where(Tinkoff_invest_tokens.user_id == user_id).execute()
        await update.message.reply_text(f'Пользователь удалён! Если вновь понадобится бот, запусти команду /start')
    else:
        await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text='Привет! Я не нашёл тебя в базе данных. '
                        'Для начала отправь команду /start'
                    )
   
    
def main():
    # соединяемся с базой данных, создавая таблицы, если их нет.
    connect_db()
    
    # Определяем ConversationHandler для обработки цепочки вопросов и ответов
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1_TOKEN: [MessageHandler(filters.TEXT & (~filters.COMMAND), q1_token)],
            Q2_SL: [MessageHandler(filters.TEXT & (~filters.COMMAND), q2_sl)],
            Q3_TP: [MessageHandler(filters.TEXT & (~filters.COMMAND), q3_tp)],
        },
        fallbacks=[CommandHandler('cancel', start_cancel)]
    )
    
    # Создание бота
    app = ApplicationBuilder().token(token).build()
    app.add_error_handler(error)
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_choice))
    app.add_handler(CommandHandler('delete_keyboard', delete_keyboard))
    app.add_handler(CommandHandler('choose_account', choose_account))
    app.add_handler(CommandHandler('delete_user', delete_user))
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler('change_token', change_token)],
            states={CHANGE_TOKEN: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_change_token)]},
            fallbacks=[CommandHandler('cancel', change_cancel)]
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler('change_sl', change_sl)],
            states={CHANGE_SL: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_change_sl)]},
            fallbacks=[CommandHandler('cancel', change_cancel)]
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler('change_tp', change_tp)],
            states={CHANGE_TP: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_change_tp)]},
            fallbacks=[CommandHandler('cancel', change_cancel)]
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_from_user))
    #app.run_polling(allowed_updates=Update.ALL_TYPES) # для выполнения данных, когда пришли команды когда бот отключен но пока эта функция нахуй не нужна
    app.run_polling()

    db.close()


if __name__ == '__main__':
    main()