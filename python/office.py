#!/usr/bin/env python3

import logging
import psycopg2
import os
from pyais import decode

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Параметры БД
CONN_PARAMS = {
    'host': os.getenv("DB_HOST"),
    'port': 5432,
    'dbname': os.getenv("DB_DATABASE"),
    'user': os.getenv("DB_USERNAME"),
    'password': os.getenv("DB_PASSWORD")
}
TABLE_NAME = 'ships_movement_raw_data'
TARGET_TABLE = 'ships_movements'

def insert_ship_movement(conn, ship_data, last_position_time):
    try:
        ship_data_with_extra = ship_data.copy()
        ship_data_with_extra['last_position_time'] = last_position_time
        with conn.cursor() as cur:
             all_columns = list(ship_data.keys()) + ['created_at']
             all_placeholders = [f'%({k})s' for k in ship_data] + ['NOW()']
             cur.execute(f"""
                    INSERT INTO {TARGET_TABLE} ({', '.join(all_columns)})
                    VALUES ({', '.join(all_placeholders)})
                """, ship_data_with_extra)
        conn.commit()
#         logger.info(f"Запись добавлена: MMSI={ship_data.get('mmsi')}")
    except Exception as e:
        logger.error(f"Ошибка вставки: {e}\nДанные: {ship_data}")
        conn.rollback()

def process_message(msg_bytes, row_id, created_at):
    msg_bytes = msg_bytes.strip("b'")
    try:
        msg = decode(msg_bytes)
        if not msg: return

        ship_data = {
            k: (
                str(getattr(msg, k))
                if getattr(msg, k) is not None  # если значение не None — преобразуем в строку
                else None  # если значение None — оставляем None
            )
            if hasattr(msg, k)  # если поле есть в объекте
            else None  # если поля нет — None
            for k in [
                'mmsi', 'shipname', 'shiptype', 'lat', 'lon', 'speed', 'course',
                'heading', 'turn', 'status', 'msg_type', 'to_bow', 'to_stern',
                'to_port', 'to_starboard', 'destination', 'callsign', 'imo',
                'draught', 'last_position_time'
            ]
        }

        if 'mmsi' not in ship_data or ship_data['mmsi'] is None:
            logger.warning(f"Нет MMSI: {row_id}")
            return

        with psycopg2.connect(**CONN_PARAMS) as conn:
            insert_ship_movement(conn, ship_data, created_at)
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {TABLE_NAME} SET is_checked = true WHERE id = %s",
                    (row_id,)
                )
            conn.commit()

    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")

def main():
    try:
        with psycopg2.connect(**CONN_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT id, data, created_at FROM {TABLE_NAME} WHERE is_checked = false")
                for row_id, msg_bytes, created_at in cur.fetchall():
                    process_message(msg_bytes, row_id, created_at)
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")


# if __name__ == "__main__":
#     main()
