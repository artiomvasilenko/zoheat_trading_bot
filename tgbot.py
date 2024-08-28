
import mydata
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    )
from telegram.ext import (
    Updater,
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
from tinkoff.invest.exceptions import RequestError
import uuid
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation
from decimal import Decimal

# Текущий статус заявки (поручения)
execution_report_status = {
    0: None,
    1: 'Исполнена',
    2: 'Отклонена',
    3: 'Отменена пользователем',
    4: 'Новая',
    5: 'Частично исполнена',
}


# Токен вашего бота
TOKEN = mydata.TOKENTG
db = SqliteDatabase('tdata.db')
class Tinkoff_invest_tokens(Model):
        user_id = IntegerField(unique=True)
        token = CharField()
        quatation = IntegerField()
        sl = IntegerField()
        tp = IntegerField()
        account = CharField(null=True)
        
        class Meta:
            database = db

def connect_db():
    db.connect()     
    db.create_tables([Tinkoff_invest_tokens, ])

Q1_TOKEN, Q2_QUATATION, Q3_SL, Q4_TP = range(4)

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
    
def find_instrument(query):
    '''Ищет инстументы по тикеру
    Возвращает объект с инструментами либо пустой массив [] если ничего не найдено
    '''
    with Client(mydata.TOKEN) as client:
        return client.instruments.find_instrument(query=query, api_trade_available_flag=True, instrument_kind=2) 

# Обработчик текстовых сообщений
async def text_from_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if check_token_in_base(update.message.from_user.id):
        instruments = find_instrument(user_message.upper())
        if instruments.instruments == []:
            await update.message.reply_text(f'По запросу "{user_message}" ничего не найдено.')
        else:
            keyboard = [[InlineKeyboardButton(f'{ins.name}', callback_data='text_from_user' + ins.uid)] for ins in instruments.instruments]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('По запросу найдены следующие акции. Выбери каким торговать: ', reply_markup=reply_markup)       



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
        try:
            result = client.users.get_accounts()
            return result
        except RequestError as e:
            print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)

   
async def choose_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''Функция выбора аккаунта для торговли и занесение номера аккаунта в БД'''
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
    
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''Функция обработки выбора аккаунта choose_account'''
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('choose_account_'):
        data = query.data.replace('choose_account_', '')
        await save_choosed_account_to_bd(query.from_user.id, data)
        await query.edit_message_text(text=f'Аккаунт {data} сохранен!') 
         
    if query.data.startswith('text_from_user'):
        data = query.data.replace('text_from_user', '')
        await query.edit_message_text(text=f'Выставляю ордер...')
        result = post_order(user_id=query.from_user.id, instrument_uid=data)
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
            sl = post_stop_loss(query.from_user.id, data)
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
            tp = post_take_profit(query.from_user.id, data)
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
        else:
            await query.edit_message_text(
                text=f'ОРДЕР НЕ ВЫСТАВЛЕН'
                f'Биржевой идентификатор заявки: {result.order_id}\n'
                f'Текущий статус заявки: {result.execution_report_status}\n'
                f'Дополнительные данные об исполнении заявки: {result.message}\n'
                )
            
def post_order(user_id, instrument_uid):
    '''
    Функция выставляет ордер.
    Принимает значения:
        user_id - для выставления ордера согласно данных из БД
        instrument_id - для выставления ордера согласно запросу
    Возвращает результат ордера
    '''
    user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
    with Client(user.token) as client:
        order = client.orders.post_order(
            instrument_id=instrument_uid,
            quantity=user.quatation,       # кол-во лотов
            direction=1,                     # 1 - покупка, 2 - продажа
            account_id=user.account,
            order_type=2,       # 1 - limit, 2 - market, 3 - bestprice
            order_id=uuid.uuid4().hex
            )
        return order
    
def post_stop_loss(user_id, instrument_uid):
    '''
    Функция выставляет стоп лос по заявке
    Принимает значения:
        user_id - для выставления ордера согласно данных из БД
        instrument_id - для выставления ордера согласно запросу
        
    Возвращает результат заявки
    '''
    # получаем данные юзера из БД
    user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
    result = {}
    with Client(user.token) as client:
        # получение последней стоимости инструмента
        last_price = client.market_data.get_last_prices(
            instrument_id=[instrument_uid]).last_prices[0].price
        # перевод в decimal
        last_price = quotation_to_decimal(last_price)
        # расчёт цены с тп
        calculated_price = last_price - last_price * Decimal(user.sl / 100)
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
            quantity=user.quatation,
            price=decimal_to_quotation(Decimal(calculated_price)),
            stop_price=decimal_to_quotation(Decimal(calculated_price)),
            direction=2, # 1-buy, 2-sell
            account_id=user.account,
            stop_order_type=2,      # 1-tp, 2-sl, 3-slimit
            expiration_type=1,  # 1-до отмены, 2-до даты
            ).stop_order_id
        return result
    
def post_take_profit(user_id, instrument_uid):
    '''
    Функция выставляет стоп лос по заявке
    Принимает значения:
        user_id - для выставления ордера согласно данных из БД
        instrument_id - для выставления ордера согласно запросу
        
    Возвращает результат заявки
    '''
    # получаем данные юзера из БД
    user = Tinkoff_invest_tokens.get(Tinkoff_invest_tokens.user_id == user_id)
    result = {}
    
    with Client(user.token) as client:
        # получение последней стоимости инструмента
        last_price = client.market_data.get_last_prices(
            instrument_id=[instrument_uid]).last_prices[0].price
        # перевод в decimal
        last_price = quotation_to_decimal(last_price)
        # расчёт цены с тп
        calculated_price = last_price + last_price * Decimal(user.tp / 100)
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
            quantity=user.quatation,
            price=decimal_to_quotation(Decimal(calculated_price)),
            stop_price=decimal_to_quotation(Decimal(calculated_price)),
            direction=2, # 1-buy, 2-sell
            account_id=user.account,
            stop_order_type=1,      # 1-tp, 2-sl, 3-slimit
            expiration_type=1,  # 1-до отмены, 2-до даты
            ).stop_order_id
        return result

           

# Обработчик ошибок
async def error(update: Update, context: CallbackContext):
    print(update, context.error)
    
def check_token_in_base(user_id):
    user = Tinkoff_invest_tokens.select().where(Tinkoff_invest_tokens.user_id == user_id)
    return True if user else False

async def q1_token(update: Update, context: CallbackContext):
    context.user_data['q1_token'] = update.message.text
    await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text='Каким лотом торговать? Напиши целое число.'
                )
    return Q2_QUATATION

async def q2_quatation(update: Update, context: CallbackContext):
    context.user_data['q2_quatation'] = update.message.text
    await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text='Какой Stop Loss устанавливать, в %? Напиши целое число.'
                )
    return Q3_SL

async def q3_sl(update: Update, context: CallbackContext):
    context.user_data['q3_sl'] = update.message.text
    await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text='Какой Take Profit устанавливать, в %? Напиши целое число.'
                )
    return Q4_TP

async def q4_tp(update: Update, context: CallbackContext):
    context.user_data['q4_tp'] = update.message.text
    user_id = update.message.from_user.id
    
    # запись в базу данных
    Tinkoff_invest_tokens().create(
        user_id=user_id, 
        token=context.user_data['q1_token'],
        quatation=context.user_data['q2_quatation'],
        sl=context.user_data['q3_sl'],
        tp=context.user_data['q4_tp'],
        )
    await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text='Всё успешно. Теперь выбери аккаунт с которого будем вести торговлю.'
                'Набери команду /choose_account'
                )
    return ConversationHandler.END

# Отмена стартового опроса
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Понимаешь, без этого робот работать не будет. Не бойся, это безопасно.')
    return ConversationHandler.END

def started_conversation():
    pass
   
    
def main():
    # соединяемся с базой данных, создавая таблицы, если их нет.
    connect_db()
    
    # Определяем ConversationHandler для обработки цепочки вопросов и ответов
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1_TOKEN: [MessageHandler(filters.TEXT & (~filters.COMMAND), q1_token)],
            Q2_QUATATION: [MessageHandler(filters.TEXT & (~filters.COMMAND), q2_quatation)],
            Q3_SL: [MessageHandler(filters.TEXT & (~filters.COMMAND), q3_sl)],
            Q4_TP: [MessageHandler(filters.TEXT & (~filters.COMMAND), q4_tp)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Создание бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_error_handler(error)
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_from_user))
    app.add_handler(CallbackQueryHandler(handle_choice))
    app.add_handler(CommandHandler('delete_keyboard', delete_keyboard))
    app.add_handler(CommandHandler('choose_account', choose_account))
    #app.run_polling(allowed_updates=Update.ALL_TYPES) # для выполнения данных, когда пришли команды когда бот отключен
    app.run_polling()

    db.close()


if __name__ == '__main__':
    main()