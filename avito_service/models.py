from peewee import PostgresqlDatabase, PrimaryKeyField, IntegerField, CharField, FloatField, DateTimeField,InternalError, Model, DoesNotExist, TextField, BooleanField, ProgrammingError, ForeignKeyField
from datetime import datetime, timedelta
import psycopg2
import re
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()

user = os.getenv('POSTGRES_USER')
admin_id = os.getenv('TELEGRAM_ADMIN_ID')
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

class User(BaseModel):
    id = IntegerField(primary_key=True, null=False)
    username = CharField(max_length=255, null=True)
    full_name = CharField(max_length=255)
    search_strings = TextField()
    is_admin = BooleanField(default=False)
    paid_till = DateTimeField(default=datetime.now() + timedelta(1))
    # paid_till = DateTimeField(default=datetime.now() + timedelta(0, 20))

class Item(BaseModel):
    id = PrimaryKeyField(null=False)
    user = ForeignKeyField(User, backref='items')
    name = CharField(max_length=255)
    link = TextField()
    price = CharField(max_length=30)
    img_link = TextField()
    linkIsSended = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)
    local_time_published_str = CharField(max_length=10, null=True)

def get_user(user_id):
    try:
        return User.select().where(User.id == user_id).get()
    except DoesNotExist as de:
        user_exist = False

def add_user(user, search_string):
    user_exist = True
    res_user = None

    try:
        res_user = User.select().where(User.id == user['id']).get()
    except DoesNotExist as de:
        user_exist = False

    if (user_exist == False):
        full_name = None
        try:
            full_name = getattr(user, 'full_name')
        except:
            full_name = '{} {}'.format(user['first_name'], user['last_name'])
        res_user = User.create(
            id=int(user['id']),
            username=user['username'],
            full_name=full_name,
            is_admin=int(user['id']) == int(admin_id),
            search_strings=json.dumps([search_string])
        )

    return [user_exist == False, res_user]

def add_item(name, link, img_link, price, local_time_published_str, linkIsSended, user_id):
    item_exist = True
    item = None
    price = re.sub(r'[^0-9.]+', r'', price)
    local_time_published_str = re.search(r'(2[0-3]|[0-1]\d):[0-5]\d', local_time_published_str)
    local_time_published_str = local_time_published_str[0] if local_time_published_str else None

    try:
        item = Item.select().where(
            (Item.name == name.strip()) & 
            (Item.price == price)
        ).get()
    except DoesNotExist as de:
        item_exist = False
 
    if (item_exist == False):
        item = Item.create(
            name=name.strip(),
            link=link,
            price=price,
            img_link=img_link,
            user=user_id,
            linkIsSended=linkIsSended,
            local_time_published_str=local_time_published_str
        )
    return item_exist == False

def get_not_sended_items(user_id):
    items = None
    try:
        items = Item.select().where((Item.linkIsSended == False) & (Item.user == user_id))
    except DoesNotExist:
        items = None

    if items != None:
        for item in items:
            item.linkIsSended = True
        Item.bulk_update(items, [Item.linkIsSended])
        return items

try:
    db.connect()
    # Item.drop_table()
    # User.drop_table()
    print('[DB] Connected')
    User.create_table()
    print('[DB] User table created')
    Item.create_table()
    print('[DB] Item table created')
except InternalError as px:
    print(str(px))
