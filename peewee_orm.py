from peewee_orm import *


db = SqliteDatabase('db.sqlite3')   
db.connect()

class Enterstat_name(Model):
    name = CharField()
    link = CharField()
    class Meta:
        database = db
        
all = Enterstat_name.select()

for a in all:
    print(a.name, a.link)

db.close()


