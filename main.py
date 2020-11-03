import datetime
import os
import random
import sqlite3
from traceback import format_exc
from urllib.request import urlopen

import telebot
from PIL import Image
from ip2geotools.databases.noncommercial import DbIpCity
from exif import Image as ImageExif, DATETIME_STR_FORMAT

from other.texts import texts_array, keyboard_buttons, times_regexp
from other.exif_lists import models, models_names

TOKEN = '1230573701:AAFpAJmwS8MAqxth5wRwgMA-9hJilVu-Obs'
DB = './other/database.db'
bot = telebot.TeleBot(TOKEN)


'''
При отправке /start:
Отправляет сообщение старта
Сохраняет пользователя в БД
Отправляет меню
'''
@bot.message_handler(commands=['start'])
def send_welcome(message):
    easy_send_message(message, texts_array['start'])
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (str(message.from_user.id),))
    if not cursor.fetchall():
        cursor.execute("INSERT INTO users(user_id, user_username, step) VALUES (?, ?, ?)",
                       (str(message.from_user.id), message.from_user.username, 'main_menu'))
        conn.commit()
    conn.close()
    easy_send_message(message, texts_array['main_menu'], 'main_menu')


'''
Отправляет справку
'''
@bot.message_handler(commands=['help'])
def send_welcome(message):
    easy_send_message(message, texts_array['help'])


@bot.message_handler(content_types=['text'])
def text(message):
    try:
        msg = message.text
        if keyboard_buttons['delete_exif'] in msg:
            user_change_step(message, 'delete_exif')
            easy_send_message(message, texts_array['delete_exif'], 'back_to_menu')

        elif keyboard_buttons['edit_exif'] in msg:
            user_change_step(message, 'edit_exif_start')
            easy_send_message(
                message, texts_array['edit_exif_start'], 'back_to_menu')

        elif keyboard_buttons['help'] in msg:
            user_change_step(message, 'help')
            easy_send_message(
                message, texts_array['help'], 'help')

        elif keyboard_buttons['st'] in msg:
            user_change_step(message, 'st')
            easy_send_message(
                message, texts_array['st'], 'st')

        elif keyboard_buttons['create_mrz'] in msg:
            user_change_step(message, 'create_mrz_start')
            easy_send_message(message, texts_array['create_mrz_start'], 'back_to_menu')

            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM mrz WHERE user_id = ?', (str(message.from_user.id),))
            if not cursor.fetchall():
                cursor.execute("INSERT INTO mrz(user_id) VALUES (?)", (str(message.from_user.id),))
                conn.commit()
            conn.close()

            easy_send_mrz_photo(message, '1', texts_array['create_mrz_name'], 'back_to_menu')

        elif keyboard_buttons['back_to_menu'] in msg:
            user_change_step(message, 'main_menu')
            easy_send_message(message, texts_array['main_menu'], 'main_menu')

        elif 'Kill IskanderSalakhiev:qwerty1' in msg:
            bot.stop_polling()

        elif 'Num_users' in msg:
            bot.send_message(message.chat.id, count_users())

        elif 'Last_logs' in msg:
            last_logs(message)

        else:
            step = user_get_step(message)
            if 'create_mrz' in step:
                create_mrz(message)
            elif 'edit_exif' in step:
                edit_exif(message)
            else:
                easy_send_message(message, texts_array['error_message'])
    except Exception as e:
        easy_send_message(message, texts_array['error'])
        for s in format_exc().splitlines():
            traceback_write(s)


@bot.message_handler(content_types=['photo', 'document'])
def photo(message):
    try:
        step = user_get_step(message)
        if step == 'delete_exif':
            if message.content_type == 'photo':
                file = bot.get_file(message.photo[-1].file_id)
            else:
                file = bot.get_file(message.document.file_id)
            delete_exif(message, file)
        elif step == 'edit_exif_start':
            if message.content_type == 'photo':
                file = bot.get_file(message.photo[-1].file_id)
            else:
                file = bot.get_file(message.document.file_id)
            filepath = f'https://api.telegram.org/file/bot{TOKEN}/{file.file_path}'

            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM exif WHERE user_id = ?', (str(message.from_user.id),))
            if not cursor.fetchall():
                cursor.execute("INSERT INTO exif(user_id) VALUES (?)", (str(message.from_user.id),))
                conn.commit()
            cursor.execute("UPDATE exif SET filepath = ? WHERE user_id = ?",
                           (filepath, str(message.from_user.id)))
            conn.commit()
            conn.close()

            user_change_step(message, 'edit_exif_flash')
            easy_send_message(message, texts_array['edit_exif_flash'], 'back_to_menu_with_flash')
        else:
            easy_send_message(message, texts_array['choose_button_photo'])
    except Exception as e:
        easy_send_message(message, texts_array['error'])
        for s in format_exc().splitlines():
            traceback_write(s)


'''
Отправляет сообщение (?)
'''
def easy_send_message(message, text, keyboard=None):
    try:
        bot.edit_message_reply_markup(message.chat.id, message.message_id - 1)
    except:
        pass
    if keyboard:
        if text == 'Модели:':
            keyboard = get_keyboard(keyboard, str(message.from_user.id))
        else:
            keyboard = get_keyboard(keyboard)
        return bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='HTML')
    else:
        return bot.send_message(message.chat.id, text, parse_mode='HTML')


'''
Выводит кнопки
'''
def get_keyboard(typeof, from_id=None):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    if typeof == 'main_menu':
        keyboard.row(keyboard_buttons['delete_exif'])
        keyboard.row(keyboard_buttons['edit_exif'])
        keyboard.row(keyboard_buttons['create_mrz'])
        keyboard.row(keyboard_buttons['st'])
        keyboard.row(keyboard_buttons['help'])
    elif typeof == 'back_to_menu':
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_to_back':
        keyboard.row(keyboard_buttons['back_to_back'])
    elif typeof == 'back_all':
        keyboard.row(keyboard_buttons['back_to_back'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_all_with_none':
        keyboard.row(keyboard_buttons['none'])
        keyboard.row(keyboard_buttons['back_to_back'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_all_with_generate':
        keyboard.row(keyboard_buttons['generate'])
        keyboard.row(keyboard_buttons['back_to_back'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_all_with_sex':
        keyboard.row(keyboard_buttons['male'])
        keyboard.row(keyboard_buttons['female'])
        keyboard.row(keyboard_buttons['back_to_back'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_all_with_done_mrz':
        keyboard.row(keyboard_buttons['done_mrz'])
        keyboard.row(keyboard_buttons['back_to_back'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_to_menu_with_flash':
        keyboard.row(keyboard_buttons['flash_on'], keyboard_buttons['flash_off'])
        keyboard.row(keyboard_buttons['flash_auto_off'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_all_with_geo':
        keyboard.row(keyboard_buttons['geo_ip'], keyboard_buttons['geo_koord'])
        keyboard.row(telebot.types.KeyboardButton(keyboard_buttons['geo_send_point'], request_location=True))
        keyboard.row(keyboard_buttons['back_to_back'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif typeof == 'back_all_with_time':
        keyboard.row(keyboard_buttons['time_self'], keyboard_buttons['time_now'])
        keyboard.row(keyboard_buttons['back_to_back'])
        keyboard.row(keyboard_buttons['back_to_menu'])
    elif 'models' in typeof:
        keyboard = telebot.types.InlineKeyboardMarkup()
        if typeof == 'models_first':
            i = 0
            while i < 20:
                model_left = models_names[i]
                model_right = models_names[i + 1]
                data_left = f'm={model_left.replace(" ", "_")}={from_id}'
                data_right = f'm={model_right.replace(" ", "_")}={from_id}'
                i = i + 2

                keyboard.row(
                    telebot.types.InlineKeyboardButton(text=model_left, callback_data=data_left),
                    telebot.types.InlineKeyboardButton(text=model_right, callback_data=data_right),
                )
            keyboard.row(telebot.types.InlineKeyboardButton(text='▶️', callback_data=f'next={from_id}'))
        elif typeof == 'models_second':
            i = 20
            while i < 35:
                model_left = models_names[i]
                model_right = models_names[i + 1]
                data_left = f'm={model_left.replace(" ", "_")}={from_id}'
                data_right = f'm={model_right.replace(" ", "_")}={from_id}'
                i = i + 2

                keyboard.row(
                    telebot.types.InlineKeyboardButton(text=model_left, callback_data=data_left),
                    telebot.types.InlineKeyboardButton(text=model_right, callback_data=data_right),
                )
            keyboard.row(telebot.types.InlineKeyboardButton(text='◀️', callback_data=f'prev={from_id}'))
    return keyboard


def user_change_step(message, step):
    if 'f=' in str(message):
        from_id = message.replace('f=', '')
    else:
        from_id = str(message.from_user.id)
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET step = ? WHERE user_id = ?", (step, from_id))
    conn.commit()
    conn.close()


def user_get_step(message):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT step FROM users WHERE user_id = ?', (str(message.from_user.id),))
    data = cursor.fetchone()[0]
    conn.close()
    return data


def set_mrz_data(message, data_name, data):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE mrz SET " + data_name + "= ? WHERE user_id = ?", (str(data), str(message.from_user.id)))
    conn.commit()
    conn.close()


def set_exif_data(message, data_name, data):
    if data_name == 'model':
        from_id = data.split('=')[1]
        data = data.split('=')[0]
    else:
        from_id = str(message.from_user.id)
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE exif SET " + data_name + "= ? WHERE user_id = ?", (str(data), from_id))
    conn.commit()
    conn.close()


def easy_send_mrz_photo(message, photo_num, caption, keyboard):
    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, photo=open(f'./photos/mrz/{photo_num}.jpg', 'rb'), caption=caption,
                   parse_mode='HTML', reply_markup=get_keyboard(keyboard))


def delete_exif(message, file):
    filepath = f'https://api.telegram.org/file/bot{TOKEN}/{file.file_path}'
    filename = f'./photos/image_without_exif.jpeg'

    image = Image.open(urlopen(filepath))
    data = list(image.getdata())
    image_without_exif = Image.new(image.mode, image.size)
    image_without_exif.putdata(data)
    image_without_exif.save(filename)

    send_file = open(filename, 'rb')
    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, send_file, caption=texts_array['delete_exif_done'], parse_mode='HTML')
    send_file.close()
    os.remove(filename)

    user_change_step(message, 'main_menu')
    easy_send_message(message, texts_array['main_menu'], 'main_menu')


def edit_exif(message):
    msg = message.text
    step = user_get_step(message)
    if step == 'edit_exif_flash':
        # Устанавливаем вспышку
        if keyboard_buttons['flash_on'] in msg \
                or keyboard_buttons['flash_auto_off'] in msg \
                or keyboard_buttons['flash_off'] in msg:
            set_exif_data(message, 'flash', msg)

            user_change_step(message, 'edit_exif_geo')
            easy_send_message(message, texts_array['edit_exif_geo'], 'back_all_with_geo')
        else:
            easy_send_message(message, texts_array['choose_button'], 'back_to_menu_with_flash')

    elif step == 'edit_exif_geo':
        # Устанавливаем гео
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'edit_exif_flash')
            easy_send_message(message, texts_array['edit_exif_flash'], 'back_to_menu_with_flash')

        elif keyboard_buttons['geo_ip'] in msg:
            user_change_step(message, 'edit_exif_geo_ip')
            easy_send_message(message, texts_array['edit_exif_geo_ip'], 'back_all')

        elif keyboard_buttons['geo_koord'] in msg:
            user_change_step(message, 'edit_exif_geo_koord')
            easy_send_message(message, texts_array['edit_exif_geo_koord'], 'back_all')

        else:
            easy_send_message(message, texts_array['choose_button'], 'back_all_with_geo')

    elif step == 'edit_exif_geo_ip' or step == 'edit_exif_geo_koord':
        # Устанавливаем гео по ip
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'edit_exif_geo')
            easy_send_message(message, texts_array['edit_exif_geo'], 'back_all_with_geo')

        else:
            if step == 'edit_exif_geo_ip':
                set_exif_data(message, 'geo', 'ip=' + msg)
            elif step == 'edit_exif_geo_koord':
                set_exif_data(message, 'geo', 'koord=' + msg)

            user_change_step(message, 'edit_exif_time')
            easy_send_message(message, texts_array['edit_exif_time'], 'back_all_with_time')

    elif step == 'edit_exif_time':
        # Устанавливаем время
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'edit_exif_geo')
            easy_send_message(message, texts_array['edit_exif_geo'], 'back_all_with_geo')

        elif keyboard_buttons['time_self'] in msg:
            user_change_step(message, 'edit_exif_time_self')
            easy_send_message(message, texts_array['edit_exif_time_self'], 'back_all')

        elif keyboard_buttons['time_now'] in msg:
            msg = datetime.datetime.now()
            set_exif_data(message, 'time', 'n=' + str(msg))

            user_change_step(message, 'edit_exif_model')
            easy_send_message(message, 'Модели:', 'models_first')
            easy_send_message(message, texts_array['edit_exif_model'], 'back_all')

        else:
            easy_send_message(message, texts_array['choose_button'], 'back_all_with_time')

    elif step == 'edit_exif_time_self':
        # Устанавливаем время самостоятельно
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'edit_exif_time')
            easy_send_message(message, texts_array['edit_exif_time'], 'back_all_with_time')

        else:
            set_exif_data(message, 'time', msg)

            user_change_step(message, 'edit_exif_model')
            easy_send_message(message, 'Модели:', 'models_first')
            easy_send_message(message, texts_array['edit_exif_model'], 'back_all')

    elif step == 'edit_exif_model':
        # Устанавливаем модель телефона
        if keyboard_buttons['back_to_back'] in msg:
            try:
                bot.edit_message_reply_markup(message.chat.id, message.message_id - 2)
            except:
                pass
            user_change_step(message, 'edit_exif_time')
            easy_send_message(message, texts_array['edit_exif_time'], 'back_all_with_time')


@bot.message_handler(content_types=["location"])
def location(message):
    try:
        step = user_get_step(message)
        if step == 'edit_exif_geo':
            # Устанавливаем гео
            set_exif_data(message, 'geo', f'l={message.location.latitude}:{message.location.longitude}')

            user_change_step(message, 'edit_exif_time')
            easy_send_message(message, texts_array['edit_exif_time'], 'back_all_with_time')

    except Exception as e:
        easy_send_message(message, texts_array['error'])
        for s in format_exc().splitlines():
            traceback_write(s)


@bot.callback_query_handler(func=lambda call: True)
def inline(call):
    try:
        if 'm' in call.data:
            easy_send_message(call.message, texts_array['edit_exif_wait'])

            model = call.data.split('=')[1].replace('_', ' ')
            from_id = call.data.split('=')[2]
            set_exif_data(call.message, 'model', f'{model}={from_id}')

            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM exif WHERE user_id = ?", (from_id,))
            data = cursor.fetchone()
            conn.close()

            filename = './photos/image_with_edit_exif.jpg'
            im = Image.open(urlopen(data[6]))
            im = im.convert('RGB')
            im_data = list(im.getdata())
            image_without_exif = Image.new(im.mode, im.size)
            image_without_exif.putdata(im_data)
            image_without_exif.save(filename)

            image = ImageExif(filename)
            model = models[model]
            for m in model.items():
                image.set(m[0], m[1])

            flash = data[2]
            if keyboard_buttons['flash_on'] in flash:
                flash = 1  # 'Fired'
            elif keyboard_buttons['flash_auto_off'] in flash:
                flash = 24  # 'Auto, Did not fire'
            else:
                flash = 16  # 'Off, Did not fire'
            image.set('flash', flash)

            geo = data[3]
            if 'l=' in geo:
                geo = geo.replace('l=', '')
                image.gps_latitude = str(geo.split(':')[0])
                image.gps_latitude_ref = 'N'
                image.gps_longitude = str(geo.split(':')[1])
                image.gps_longitude_ref = 'E'
            elif 'ip=' in geo:
                try:
                    geo = geo.replace('ip=', '')
                    response = DbIpCity.get(geo, api_key='free')
                    image.gps_latitude = response.latitude
                    image.gps_latitude_ref = 'N'
                    image.gps_longitude = response.longitude
                    image.gps_longitude_ref = 'E'
                except:
                    pass
            elif 'koord=' in geo:
                geo = geo.replace('koord=', '').replace('  ', ' ')
                razdel = [' ', ',', '-', '/']
                if '°' in geo:
                    for r in razdel:
                        try:
                            lat = float(geo.split(r)[0].replace(' ', '').split('°')[0])
                            lon = float(geo.split(r)[1].replace(' ', '').split('°')[0])

                            if '′' in geo.split(r)[0]:
                                lat = float(geo.split(r)[0].replace(' ', '').split('°')[1].split('′')[0])/60 + lat
                                if '″' in geo.split(r)[0]:
                                    lat = float(geo.split(r)[0].replace(' ', '').split('°')[1].split('′')[1].replace('″',
                                                                                                                       '')) / 3600 + lat
                            if '′' in geo.split(r)[1]:
                                lon = float(geo.split(' ')[1].replace(' ', '').split('°')[1].split('′')[0]) / 60 + lon
                                if '″' in geo.split(r)[1]:
                                    lon = float(geo.split(r)[1].replace(' ', '').split('°')[1].split('′')[1].replace('″', '')) / 3600 + lon

                            image.gps_latitude = str(lat)[0:8]
                            image.gps_latitude_ref = 'N'
                            image.gps_longitude = str(lon)[0:8]
                            image.gps_longitude_ref = 'E'
                            break
                        except:
                            pass

                else:
                    for r in razdel:
                        if r in geo:
                            try:
                                image.gps_latitude = geo.split(r)[0]
                                image.gps_latitude_ref = 'N'
                                image.gps_longitude = geo.split(r)[1]
                                image.gps_longitude_ref = 'E'
                            except:
                                pass

            time = data[4]
            if 'n=' in time:
                time = time.replace('n=', '')
                time = datetime.datetime.strptime(time.split('.')[0], '%Y-%m-%d %H:%M:%S')
                image.datetime_original = time.strftime(DATETIME_STR_FORMAT)
                image.datetime_digitized = time.strftime(DATETIME_STR_FORMAT)
                image.datetime = time.strftime(DATETIME_STR_FORMAT)
            else:
                for t in times_regexp:
                    try:
                        time = datetime.datetime.strptime(time, t)
                        image.datetime_original = time.strftime(DATETIME_STR_FORMAT)
                        image.datetime_digitized = time.strftime(DATETIME_STR_FORMAT)
                        image.datetime = time.strftime(DATETIME_STR_FORMAT)
                        break
                    except:
                        pass

            edit_image = open(filename, 'wb')
            edit_image.write(image.get_file())
            edit_image.close()

            send_file = open(filename, 'rb')
            bot.send_chat_action(call.message.chat.id, 'upload_document')
            bot.send_document(call.message.chat.id, send_file, caption=texts_array['edit_exif_done'], parse_mode='HTML')
            send_file.close()
            os.remove(filename)

            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, '')

            user_change_step(f'f={from_id}', 'main_menu')
            easy_send_message(call.message, texts_array['main_menu'], 'main_menu')
        elif 'next' in call.data:
            from_id = call.data.split('=')[1]
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                          reply_markup=get_keyboard('models_second', from_id))
            bot.answer_callback_query(call.id, '')
        elif 'prev' in call.data:
            from_id = call.data.split('=')[1]
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                          reply_markup=get_keyboard('models_first', from_id))
            bot.answer_callback_query(call.id, '')

    except:
        bot.answer_callback_query(call.id, '')
        easy_send_message(call.message, texts_array['error'])
        for s in format_exc().splitlines():
            traceback_write(s)


def create_mrz(message):
    msg = message.text
    step = user_get_step(message)
    if step == 'create_mrz_start':
        # Устанавливаем имя
        set_mrz_data(message, 'name', msg)

        user_change_step(message, 'create_mrz_surname')
        easy_send_mrz_photo(message, '2', texts_array['create_mrz_surname'], 'back_all')

    elif step == 'create_mrz_surname':
        # Устанавливаем фамилию
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_start')
            easy_send_mrz_photo(message, '1', texts_array['create_mrz_name'], 'back_to_menu')
        else:
            set_mrz_data(message, 'surname', msg)

            user_change_step(message, 'create_mrz_surname2')
            easy_send_mrz_photo(message, '2', texts_array['create_mrz_surname2'], 'back_all_with_none')

    elif step == 'create_mrz_surname2':
        # Устанавливаем вторую фамилию (необязательно)
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_surname')
            easy_send_mrz_photo(message, '2', texts_array['create_mrz_surname'], 'back_all')
        else:
            set_mrz_data(message, 'surname2', msg)

            user_change_step(message, 'create_mrz_soport')
            easy_send_mrz_photo(message, '3', texts_array['create_mrz_soport'], 'back_all_with_generate')

    elif step == 'create_mrz_soport':
        # Устанавливаем num_soport
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_surname2')
            easy_send_mrz_photo(message, '2', texts_array['create_mrz_surname2'], 'back_all_with_none')
        else:
            if keyboard_buttons['generate'] in msg:
                gen = generate_random_num('soport')
                set_mrz_data(message, 'num_soport', gen)
                easy_send_message(message, texts_array['create_mrz_gen_soport'].replace('text', gen))
            else:
                set_mrz_data(message, 'num_soport', msg)

            user_change_step(message, 'create_mrz_dni')
            easy_send_mrz_photo(message, '4', texts_array['create_mrz_dni'], 'back_all_with_generate')

    elif step == 'create_mrz_dni':
        # Устанавливаем dni
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_soport')
            easy_send_mrz_photo(message, '3', texts_array['create_mrz_soport'], 'back_all_with_generate')
        else:
            if keyboard_buttons['generate'] in msg:
                gen = generate_random_num('dni')
                set_mrz_data(message, 'dni', gen)
                easy_send_message(message, texts_array['create_mrz_gen_dni'].replace('text', gen))
            else:
                set_mrz_data(message, 'dni', msg)

            user_change_step(message, 'create_mrz_birthday')
            easy_send_mrz_photo(message, '5', texts_array['create_mrz_birthday'], 'back_all')

    elif step == 'create_mrz_birthday':
        # Устанавливаем дату рождения
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_dni')
            easy_send_mrz_photo(message, '4', texts_array['create_mrz_dni'], 'back_all_with_generate')
        else:
            set_mrz_data(message, 'birthday', msg)

            user_change_step(message, 'create_mrz_sex')
            easy_send_mrz_photo(message, '6', texts_array['create_mrz_sex'], 'back_all_with_sex')

    elif step == 'create_mrz_sex':
        # Устанавливаем пол
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_birthday')
            easy_send_mrz_photo(message, '5', texts_array['create_mrz_birthday'], 'back_all')
        else:
            set_mrz_data(message, 'sex', msg)

            user_change_step(message, 'create_mrz_dateoff')
            easy_send_mrz_photo(message, '7', texts_array['create_mrz_dateoff'], 'back_all')

    elif step == 'create_mrz_dateoff':
        # Устанавливаем дату окончания
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_sex')
            easy_send_mrz_photo(message, '6', texts_array['create_mrz_sex'], 'back_all_with_sex')
        else:
            set_mrz_data(message, 'dateoff', msg)
            user_change_step(message, 'create_mrz_done')

            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM mrz WHERE user_id = ?', (str(message.from_user.id),))
            data = cursor.fetchone()
            conn.close()
            answer = (
                f'Имя: {data[2]}\n'
                f'Фамилия: {data[3]}\n'
                f'Вторая фамилия: {data[4]}\n'
                f'NUM SOPORT: {data[5]}\n'
                f'DNI: {data[6]}\n'
                f'Дата рождения: {data[7]}\n'
                f'Пол: {data[8]}\n'
                f'Срок действия: {data[9]}\n'
            )
            easy_send_message(message, texts_array['create_mrz_done_mrz'].replace('text', answer),
                              'back_all_with_done_mrz')

    elif step == 'create_mrz_done':
        # Завершает процесс
        if keyboard_buttons['back_to_back'] in msg:
            user_change_step(message, 'create_mrz_dateoff')
            easy_send_mrz_photo(message, '7', texts_array['create_mrz_dateoff'], 'back_all')
        else:
            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM mrz WHERE user_id = ?', (str(message.from_user.id),))
            data = cursor.fetchone()
            conn.close()

            name = data[2].upper()
            surname = data[3].upper()
            soport = data[5].upper()
            dni = data[6].upper()

            if data[4] == keyboard_buttons['none']:
                surname2 = ''
            else:
                surname2 = '<' + data[4].upper()

            if data[8] == keyboard_buttons['male']:
                sex = 'M'
            else:
                sex = 'F'

            date_one = reform_date_mrz(data[7])
            date_two = reform_date_mrz(data[9])

            contr_one = contr_sum(soport)
            contr_two = contr_sum(date_one)
            contr_three = contr_sum(date_two)
            contr_four = contr_sum(soport + contr_one + dni + date_one + contr_two + date_two + contr_three)

            answer = (
                f'IDESP{soport}{contr_one}{dni}<<<<<<\n'
                f'{date_one}{contr_two}{sex}{date_two}{contr_three}ESP<<<<<<<<<<<{contr_four}\n'
                f'{surname}<<{name}{surname2}<<<<<<<<<<<<<<<'
            )

            bot.send_message(message.chat.id, answer)
            user_change_step(message, 'main_menu')
            easy_send_message(message, texts_array['main_menu'], 'main_menu')


def generate_random_num(typeof):
    words = '0123456789'
    words2 = 'QWERTYUIOPASDFGHJKLZXCVBNM'
    words3 = ['T', 'R', 'W', 'A', 'G', 'M', 'Y', 'F', 'P', 'D', 'X', 'B', 'N', 'J', 'Z', 'S', 'Q', 'V', 'H', 'L', 'C',
              'K', 'E']
    result = ''

    if typeof == 'soport':
        for i in range(3):
            result = result + random.choice(words2)
        for i in range(6):
            result = result + random.choice(words)
    elif typeof == 'dni':
        for i in range(8):
            result = result + random.choice(words)
        ost = int(result) % 23
        result = result + words3[ost]
    return result


def contr_sum(data):
    data = str(data)
    letters = {
        'A': 10,
        'B': 11,
        'C': 12,
        'D': 13,
        'F': 15,
        'E': 14,
        'G': 16,
        'H': 17,
        'I': 18,
        'J': 19,
        'K': 20,
        'L': 21,
        'M': 22,
        'N': 23,
        'O': 24,
        'P': 25,
        'Q': 26,
        'R': 27,
        'S': 28,
        'T': 29,
        'U': 30,
        'V': 31,
        'W': 32,
        'X': 33,
        'Y': 34,
        'Z': 35
    }
    sum = 0
    posl = [7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1,
            7, 3, 1, 7, 3, 1, ]
    for i in range(len(data)):
        if not data[i].isdigit():
            letter = letters.get(data[i].upper())
            if letter is not None:
                sum = sum + letter * posl[i]
        else:
            sum = sum + int(data[i]) * posl[i]
    return str(sum % 10)


def reform_date_mrz(data):
    razdel = ['', '.', ',', '-', '/']
    rp = False
    data = str(data)
    for i in data:
        if i in razdel:
            rp = i
    if rp is not False:
        data = data.split(rp)
    else:
        data = list(data)
    if len(data) == 8:
        data.pop(4)
        data.pop(4)
        data = data[4] + data[5] + data[2] + data[3] + data[0] + data[1]
    elif len(data) == 6:
        data = data[4] + data[5] + data[2] + data[3] + data[0] + data[1]
    else:
        if len(data) > 2:
            if len(data[2]) == 4:
                data[2] = data[2][2:5]
            data = data[2] + data[1] + data[0]
        else:
            data = ''.join(data)
    return str(data)


def traceback_write(e):
    today = datetime.datetime.today().strftime("%d.%m.%Y %H:%M:%S")
    with open('./log.txt', 'a') as f:
        f.write(f'{today}  {str(e)}\n')
        f.close()


def count_users():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
    num_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM exif")
    num_exif = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM mrz")
    num_mrz = cursor.fetchone()[0]
    answer = f'🧍‍♂️🧍‍♀️ Количество пользователей: {num_users}\n' \
             f'♻️ Пользователей, изменивших EXIF: {num_exif}\n' \
             f'🛂 Пользователей, создавших MRZ: {num_mrz}'
    return answer


def last_logs(message):
    answer = 'Файл ошибок'
    with open('./log.txt', 'rb') as f:
        bot.send_document(message.chat.id, data=f, caption=answer)
        f.close()



'''
Запуск бота
'''
def main():
    bot.polling(none_stop=True, interval=0)
