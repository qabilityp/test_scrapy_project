# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import logging
from scrapy.exceptions import DropItem
import sqlite3


logger = logging.getLogger(__name__)


class CleaningPipeline:
    """Валидация и нормализация данных"""

    def process_item(self, item, spider):
        # Обязательные поля
        if not item.get('model') or not item.get('name') or not item.get('registration'):
            logger.warning(f"Dropped item: missing model/name/registration. Item: {item}")
            raise DropItem("Missing required fields")

        # Очистка пробега
        if item.get('mileage_raw'):
            raw = item['mileage_raw'].replace(',', '')
            try:
                item['mileage_raw'] = int(raw)
            except ValueError:
                logger.warning(f"Could not convert mileage to int: {item['mileage_raw']}")
                # оставляем как есть или можно выбросить DropItem

        # Приведение топлива к нижнему регистру
        if item.get('fuel'):
            item['fuel'] = item['fuel'].lower()

        return item


class SQLitePipeline:
    def open_spider(self, spider):
        self.conn = sqlite3.connect('bmw_cars.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT,
                name TEXT,
                mileage_raw INTEGER,
                registered TEXT,
                engine TEXT,
                range TEXT,
                exterior TEXT,
                fuel TEXT,
                transmission TEXT,
                registration TEXT UNIQUE,
                upholstery TEXT
            )
        ''')
        self.conn.commit()

    def process_item(self, item, spider):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO cars 
                (model, name, mileage_raw, registered, engine, range, exterior, fuel, transmission, registration, upholstery)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('model'),
                item.get('name'),
                item.get('mileage_raw'),
                item.get('registered'),
                item.get('engine'),
                item.get('range'),
                item.get('exterior'),
                item.get('fuel'),
                item.get('transmission'),
                item.get('registration'),
                item.get('upholstery'),
            ))
        except sqlite3.IntegrityError:
            spider.logger.warning(f"Duplicate registration ignored: {item.get('registration')}")
        return item

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()
        # commit() is called once in close_spider for performance.
        # For large-scale projects, consider batching with executemany()
        # or using SQLAlchemy with connection pooling.
