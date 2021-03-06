from bs4 import BeautifulSoup
import requests
import time
import os
import json
import logging
import warnings
import pymorphy2
import locale
from functools import wraps
from datetime import datetime
from telegram.vendor.ptb_urllib3.urllib3.exceptions import InsecureRequestWarning
from telegram.ext import CommandHandler, Job
from telegram.ext import MessageHandler, Filters
from telegram.ext import Updater, CallbackQueryHandler, CallbackContext
from telegram import ReplyKeyboardMarkup, ReplyMarkup, InlineKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton
from telegram.chataction import ChatAction
from models import add_item, get_not_sended_items, add_user, get_user
from dotenv import load_dotenv

locale.setlocale(locale.LC_ALL, 'ru_RU')
m = pymorphy2.MorphAnalyzer()
warnings.simplefilter('ignore', InsecureRequestWarning)

load_dotenv()

TTOKEN = os.getenv('TELEGRAM_API_KEY')

REQUEST_KWARGS = {
    'proxy_url': 'socks5://orbtl.s5.opennetwork.cc:999/',
    # Optional, if you need authentication:
    'urllib3_proxy_kwargs': {
        'assert_hostname': 'False',
        'cert_reqs': 'CERT_NONE',
        'username': '458644489',
        'password': 'CXz1DriW'
    }
}

ALL_COMANDS = [
    ('/start', 'Начало работы с ботом'),
    ('/stop', 'Остановить проверку новых объявлений по запросу'),
    ('/edit', 'Редактировать запрос'),
    ('/delete', 'Удалить запрос'),
]

updater = Updater(token=TTOKEN, use_context=True, request_kwargs=REQUEST_KWARGS)
dispatcher = updater.dispatcher
job_queue = updater.job_queue
bot = updater.bot

bot.set_my_commands(ALL_COMANDS)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def send_action(action):
    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(update, context, *args, **kwargs)
        return command_func
    return decorator

def get_html(url):
    print('[REST] [GET] ->', url)
    r = requests.get(url)
    return r.text

def get_publish_date(tag):
    result_dt = tag.find("div", {"class": "snippet-date-info"}).attrs['data-tooltip']
    if (result_dt):
        day, month, time = result_dt.split(' ')
        new_month = m.parse(month)[0].inflect({'nomn'}).word.title()
        year = datetime.now().year
        return datetime.strptime(' '.join([day, new_month, str(year), time]), '%d %B %Y %H:%M')
    else:
        return None

def send_item_card(chat_id, item, context, first):
    message = '<a href="{}">{}</a> продается сейчас за {}, объявление опубликовано {} в {}'.format(
        item.link,
        item.name,
        item.price,
        'сегодня' if item.created_at.date() == datetime.now().date() else datetime.strftime(item.created_at, '%e %B'),
        datetime.strftime(item.created_at, '%H:%M'),
    )
    context.bot.send_photo(chat_id=chat_id, photo=item.img_link, parse_mode='HTML', caption=message, disable_notification=first)

def check_is_user_paid(user):
    if (user.is_admin == False):
        return user.paid_till > datetime.now()
    else:
        return True

def go_live(context):
    tgrm_user = context.job.context['user']
    user = get_user(tgrm_user.id)
    chat_id = context.job.context['chat_id']
    user_is_created = len(user.items) == 0
    job = context.job
    if (check_is_user_paid(user)):
        search_strings = json.loads(user.search_strings)
        for search_string in search_strings:
            # soup = BeautifulSoup(get_html(input_text), 'html.parser')
            soup = BeautifulSoup(get_html(search_string), 'lxml')

            items = soup.find_all("div", {"class": "item__line"})
            for idx, tag in enumerate(items):
                # Старый вариант поиска проплаченых публикаций
                # is_paid_item = tag.find("span", {"class": "snippet-price-vas"})
                item = tag.find("a", {"class": "snippet-link"})
                name = item.text
                img_link = tag.find("img").attrs['src']
                link = 'https://www.avito.ru' + item.attrs['href']
                price = tag.find("span", {"class": "snippet-price"}).text
                result_dt = get_publish_date(tag)
                link_is_sended = False
                # Проверяю, что юзер только что был создан, так что не надо вываливать в него 50 сообщений)
                if (user_is_created and idx > 5):
                    link_is_sended = True
                created = add_item(name, link, img_link, price, result_dt, link_is_sended, user.id)
                # if created == False and is_paid_item == None:
                #     break
            not_sended_items = get_not_sended_items(user.id)
            if (not_sended_items):
                for idx, item in enumerate(not_sended_items):
                    send_item_card(chat_id, item, context, idx != 0)

    else:
        job.schedule_removal()
        context.bot.send_message(chat_id=chat_id, text='Срок действия оплаты закончен, просьба оплатить')

def add_job_to_queue(update, context):
    created, user = add_user(update.message.from_user, update.message.text)
    new_context = {
        'user': update.message.from_user,
        'chat_id': update.message.chat_id,
    }

    if (check_is_user_paid(user)):
        job_queue.run_repeating(go_live, interval=600, first=0, context=new_context, name=str(user.id)+'|'+str(update.message.text))
    else:
        jobs_to_remove = job_queue.get_jobs_by_name(str(user.id))
        if (bool(jobs_to_remove)):
            jobs_to_remove.schedule_removal()
        context.bot.send_message(chat_id=update.effective_chat.id, text='Срок действия оплаты закончен, просьба оплатить')

@send_action(ChatAction.TYPING)
def start(update, context):
    start_message = 'Привет! Ты можешь отправить мне ссылку с поиска на Авито и я буду присылать тебе новые объявления с совсем небольшой задержкой'
    context.bot.send_message(chat_id=update.effective_chat.id, text=start_message)

@send_action(ChatAction.TYPING)
def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Отправь ссылку на поиск с авито")

@send_action(ChatAction.TYPING)
def delete(update, context):
    result_queryes_strings = []
    user = get_user(update.message.from_user.id)
    user_search_strings = json.loads(user.search_strings)
    for search in user_search_strings:
        jobs = job_queue.get_jobs_by_name(str(update.message.from_user.id)+'|'+search)
        if (len(jobs) > 0):
            result_queryes_strings.append(jobs[0].name)

    if (len(result_queryes_strings) > 0):
        reply = ReplyKeyboardMarkup([[job.name for job in jobs]])
        context.bot.send_message(chat_id=update.effective_chat.id, reply_markup=reply, text="Выберите запрос для удаления")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="У вас нет активных запросов")

@send_action(ChatAction.TYPING)
def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Извини, я тебя не понимаю")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

delete_handler = CommandHandler('delete', delete)
dispatcher.add_handler(delete_handler)

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

main_avito = MessageHandler(Filters.text & (Filters.entity('url') | Filters.entity('text_link')), add_job_to_queue)
dispatcher.add_handler(main_avito)

updater.start_polling()