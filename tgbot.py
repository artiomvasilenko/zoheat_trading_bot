
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
from find_instrument import find_instrument


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


# Обработчик текстовых сообщений
async def text_from_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if check_token_in_base(update.message.from_user.id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f'Привет, {update.message.chat.first_name}. Your message {user_message}'
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
    keyboard = [
        [InlineKeyboardButton(f'{acc.name} - {acc.id}', callback_data=acc.id) for acc in accounts.accounts if acc.access_level == 1],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выбери аккаунт: ', reply_markup=reply_markup)
    
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''Функция обработки выбора аккаунта choose_account'''
    query = update.callback_query
    await query.answer()
    await save_choosed_account_to_bd(query.from_user.id, query.data)
    await query.edit_message_text(text=f'Аккаунт {query.data} сохранен!')  
    

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
    app.run_polling(allowed_updates=Update.ALL_TYPES)

    db.close()


if __name__ == '__main__':
    main()