# Бот для редактирования EXIF данных

### Версия 1.2.0

Файл _text.py_ содержит в себе основные сообщения для отправки ботом

Файл _main.py_ содержит в себе все функции бота


### Для работы необходимо:
1. Установить библиотеки из requirements.txt

```shell script
pip3 install -r requirements.txt
```

2. Создать базу данных database.db и произвести SQL запрос 

```sql
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Таблица: exif
DROP TABLE IF EXISTS exif;

CREATE TABLE exif (
    id       INTEGER PRIMARY KEY AUTOINCREMENT
                     UNIQUE
                     NOT NULL,
    user_id          UNIQUE,
    flash,
    geo,
    time,
    model,
    filepath
);


-- Таблица: mrz
DROP TABLE IF EXISTS mrz;

CREATE TABLE mrz (
    id         INTEGER PRIMARY KEY AUTOINCREMENT
                       UNIQUE
                       NOT NULL,
    user_id            UNIQUE,
    name,
    surname,
    surname2,
    num_soport,
    dni,
    birthday,
    sex,
    dateoff
);


-- Таблица: users
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT
                          UNIQUE
                          NOT NULL,
    user_id       STRING  UNIQUE,
    user_username STRING  UNIQUE,
    step
);


COMMIT TRANSACTION;
PRAGMA foreign_keys = on;

```

3. Внести изменения в файл констант (_constants.py) в переменную ATTRIBUTE_TYPE_MAP библиотеки exif

```python
"focal_length": (int(ExifTypes.ASCII), 0),
"lens_make": (int(ExifTypes.ASCII), 0),
"lens_model": (int(ExifTypes.ASCII), 0),
"x_resolution": (int(ExifTypes.ASCII), 0),
"y_resolution": (int(ExifTypes.ASCII), 0),
"compression": (int(ExifTypes.SHORT), 0),
"photographic_sensitivity": (int(ExifTypes.ASCII), 0),
```

