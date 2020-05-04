from peewee import PostgresqlDatabase, PrimaryKeyField, CharField, FloatField, DateTimeField, InternalError, Model, DoesNotExist, TextField, BooleanField, ProgrammingError
import datetime
import psycopg2
import re
import os
import time

user = os.getenv('POSTGRES_USER')
password = os.getenv('POSTGRES_PASSWORD')
db_name = os.getenv('POSTGRES_DB')
db_host = os.getenv('POSTGRES_HOSTNAME')
 
db = PostgresqlDatabase(
    db_name, user=user,
    password=password,
    host=db_host,
)

class BaseModel(Model):
    class Meta:
        database = db
 
class Item(BaseModel):
    id = PrimaryKeyField(null=False)
    name = CharField(max_length=255)
    link = TextField()
    price = CharField(max_length=30)
    img_link = TextField()
    linkIsSended = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now())

def add_item(name, link, img_link, price, date_published):
    item_exist = True
    price = re.sub(r'[^0-9.]+', r'', price)
    try:
        Item.select().where(Item.name == name.strip() and Item.price == price).get()
    except DoesNotExist as de:
        item_exist = False
 
    if (item_exist == False):
        row = Item(
            name=name.strip(),
            link=link,
            price=price,
            img_link=img_link
        )
        row.save()
        print('[DB] Saved item ' + name.strip())

def get_not_sended_items():
    items = None
    try:
        items = Item.select().where(Item.linkIsSended == False)
    except DoesNotExist:
        items = None

    if items != None:
        for item in items:
            item.linkIsSended = True
            item.save()
        return items

try:
    time.sleep(60)
    db.connect()
    print('[DB] Connected')
    Item.create_table()
    print('[DB] Table created')
except InternalError as px:
    print(str(px))
