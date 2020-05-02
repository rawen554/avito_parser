from bs4 import BeautifulSoup
import requests
import smtplib
import time
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from models import add_item, get_not_sended_items

def sendMessage(bodyText):
    addr_from = os.getenv('EMAIL_FROM')
    addr_to   = os.getenv('EMAIL_TO')
    password  = os.getenv('EMAIL_PASSWORD')

    msg = MIMEMultipart()
    msg['From']    = addr_from
    msg['To']      = addr_to
    msg['Subject'] = soup.title.text

    html = """\
    <html>
    <head></head>
    <body>
        <h2>Объявление:</h2>
        """+bodyText+"""
    </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    server = smtplib.SMTP_SSL(os.getenv('EMAIL_SMTP_HOST'), int(os.getenv('EMAIL_SMTP_PORT')))
    #server.set_debuglevel(True)
    #server.starttls()
    server.login(addr_from, password)
    server.send_message(msg)

yula_base_page = 'https://youla.ru/moskva?'
def get_yula_price_from(amount): return 'attributes[price][from]='+str(amount)+'00&'
def get_yula_price_to(amount): return 'attributes[price][to]='+str(amount)+'00&'
def get_yula_sort_field(sort): return 'attributes[sort_field]='+str(sort)+'&'
yula_queryes = [
    'q=ps%20vita',
    'q=nintendo%20switch'
]
def build_yula_url(amount_from, amount_to, sort, query):
    return yula_base_page+get_yula_price_from(amount_from)+get_yula_price_to(amount_to)+get_yula_sort_field(sort)+query

avito_base_page = os.getenv('AVITO_BASE_PAGE')

def build_avito_url(base, query):
    return avito_base_page+'&'+query

def get_html(url):
    print('GET ->', url)
    r = requests.get(url)
    return r.text

def check_new_items():
    bodyText = ''
    items = get_not_sended_items()
    if (items):
        for item in items:
            bodyText += '<img src="'+item.img_link+'" />'
            bodyText += '<a href="'+item.link+'"><h3>'+item.price+'</h3><h4>'+item.name+'</h4></a>'
        sendMessage(bodyText)

while True:
    soup = BeautifulSoup(get_html(avito_base_page), 'lxml')

    items = soup.find_all("div", {"class": "item__line"})
    for idx, tag in enumerate(items):
        item = tag.find("a", {"class": "snippet-link"})
        name = item.text
        img_link = tag.find("img").attrs['src']
        link = 'https://www.avito.ru' + item.attrs['href']
        price = tag.find("span", {"class": "snippet-price"}).text
        add_item(name, link, img_link, price)

    check_new_items()

    time.sleep(600)