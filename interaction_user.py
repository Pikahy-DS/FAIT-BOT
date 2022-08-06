import logging
import asyncio
from re import search
import sys
from typing import Any
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Bot, Dispatcher, types, F, Router, html
from aiogram.types import Message, KeyboardButton, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardMarkup, InlineKeyboardMarkup
import cx_Oracle
import config
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.dispatcher.fsm.storage.memory import MemoryStorage
import datetime
import time
from threading import Thread
import pyowm
from pyowm.utils.config import get_default_config
from vk_api import VkApi


import interaction_inside
import main





#-
async def weather(message: Message):
    """Функция  рассылки погоды и пар 

    Args:
        message (Message):  сообщение из которого можно достать всю инфу о пользователе
    """    
    flag_time_sleep = True
    await message.answer('Функция погода - запущена')
    bot = Bot(main.TOKEN, parse_mode="html")
    while flag_time_sleep:
        #message.answer
        date1 = datetime.datetime.now().strftime('%H:%M')
        if date1[0:2] == '22' and date1[3:5] == '53':
            weeknum = datetime.datetime.now().isocalendar()[2] % 2
            daynum = datetime.datetime.now().isocalendar()[2]
            
            select_weather_schedule_sql = """SELECT id_user from users"""
            select_weather_schedule = main.cursor.execute(select_weather_schedule_sql, ).fetchall()
            for i in select_weather_schedule:
                
                #print(i[0])
                group_name_users = """SELECT group_name from users where id_user =: id_user"""
                records = main.cursor.execute(group_name_users, [i[0]]).fetchall()
                if records[0][0] != None:
                    group_name = records[0][0]
                    print(group_name)
                    sql = """SELECT * FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                    num = main.cursor.execute(sql,
                                         {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                    
                    #print(records[0][0], daynum, weeknum)
                    #try и except в этом случае нужен для того что бы при остсутствии чата с человеком но 
                    # наличии его в базе данных пропустить его и не вызывать ошибку прирывая исполнение кода 
                    
                    print("ТУТ!")
                    print(num)
                    if num:
                        
                        try:
                            await bot.send_message(i[0],f'Доброе утро! Ваши пары на сегодня:\n')
                        except:
                            continue
                        for row in num:
                            
                            #print(row)
                            await bot.send_message(i[0],
                                                   f'<u><b>{row[1]} пара - {main.lesson_time[row[1]]}</b></u>:\n'
                                                   f'<b>Предмет:</b> {row[2]}\n<b>Препод.:</b> {row[4]}\n'
                                                   f'<b>Формат: </b>{row[3]}\n<b>Аудитория:</b> {row[5]}')
                            # bot.send_message(message.chat.id, f"http://r.sf-misis.ru/group/{num[0][0]}")
                    
                    else:
                    #     #При желании выводить погоду утром закоментировать else полностью иначе оставить
                    #     await bot.send_message(i[0],f'Доброе утро!\nУ вас сегодня нет пар!')
                    #     print("Нету пар сегодня")
                        continue

                else:
                    
                    group_name_users = """SELECT lower(FIO) from users where id_user =: id_user"""
                    records = main.cursor.execute(group_name_users, [i[0]]).fetchall()
                    teachers = records[0][0]
                    sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                    num = main.cursor.execute(sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                    #print(records[0][0], daynum, weeknum)
                    d = {}
                    for row in num:
                        key = f"{row[1]} {row[2]}"
                        if key in d:
                            d[key].append(row[0])
                        else:
                            d[key] = [row[0]]

                    if num:
                        
                        await bot.send_message(i[0],f'Доброе утро! Ваши пары на сегодня:\n')
                        for row in num:
                            key = f"{row[1]} {row[2]}"
                            if not d[key]:
                                continue
                            await bot.send_message(i[0],
                                                   f'<u><b>{row[1]} пара - {main.lesson_time[row[1]]}:</b></u>\n'
                                                   f'<b>Предмет:</b> {row[2]}\n<b>Группа(ы):</b> {", ".join(d[key])}\n'
                                                   f'<b>Формат:</b> {row[3]}\n<b>Аудитория:</b> {row[5]}')
                            #print(
                             #   f'{row[1]} пара - {lesson_time[row[1]]}:\n{row[2]}\n{", ".join(d[key])}\n{row[3]}\n{row[5]}')
                            d[key] = []

                        # bot.send_message(message.chat.id, f"http://r.sf-misis.ru/teacher/{num[0][0]}")
                    else:
                    #     #await bot.send_message(i[0],f'Доброе утро!\nУ вас сегодня нет пар!')
                    #     #print("Нету пар сегодня")
                        continue
                try:
                    
                    config_dict = get_default_config()
                    config_dict['language'] = 'RU'
                    mgr = main.owm.weather_manager()
                    observation = mgr.weather_at_place('Старый Оскол')
                    w = observation.weather
                    temp = w.temperature('celsius')['temp']
                    Wind = w.wind()
                    # Формула для определения эффективной температуры по госту 
                    effective_temp = 13.12 + 0.6215 * temp - 11.37 * ((1.5 * Wind["speed"]) ** 0.16)+ 0.3965 * temp * ((1.5 * Wind["speed"]) ** 0.16) 
                    effective_temp=round(effective_temp, 1)
                    Feeling_weather = 'Ощущается как ' + str(effective_temp) + '°C'
                    try:
                        await bot.send_message(i[0],
                                           'На улице сейчас ' + str(
                                               w.detailed_status) + '\n🌡Температура сейчас в районе ' + str(
                                               int(temp)) + ' °C\n' + '🌬Скорость ветра = ' + str(
                                               Wind['speed']) + ' м/с\n' + Feeling_weather) 
                    except:
                        print("Ошибка вывода температуры")
                        continue
                except Exception:
                    print("EROR weather")
                    await bot.send_message(i[0],
                                           'Ошибка на сервер, нет связи с сервером погоды!')

        await asyncio.sleep(60)
#-
async def delete_time_sleep_notifications(message: Message):
    """Убрать оповещения о началах пар

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    str_select_time_sleep = None
    select_time_sleep_sql = """SELECT notifications from users where id_user =: id_user"""
    select_time_sleep = main.cursor.execute(select_time_sleep_sql, [message.chat.id]).fetchall()
    #print(message.chat.id)
    update_time_sleep_sql = """UPDATE users SET notifications =: notifications where id_user =: id_user"""
    data_tuple = {'notifications': str_select_time_sleep, 'id_user': message.chat.id}
    main.cursor.execute(update_time_sleep_sql, data_tuple)
    main.conn.commit()
    #print('Успешно удалены', '====', str_select_time_sleep)

#Функция отправки сообщений  при упоминании
#-
async def send_like_message(message: Message):
    """Функция отправки сообщений  при упоминании 

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
       
    bot = Bot(main.TOKEN, parse_mode="html")
    search_like_message=True
    await message.answer('Функция send_like_message - запущена!')
    while search_like_message==True:
        group_name = """" SELECT group_name from users where id_user = 411892636"""
        select_like_message = f"""SELECT * from starostat_news  where id_news in ( select id_news
from (select INSTR(b.news_view, a.id_news) as newss, b.news_view, a.id_news from starostat_news a, users b where id_user =: id_user and (text like '%{group_name}%' )))"""
        print("Название группы=" + group_name)
        #update_rownum = """UPDATE users SET news_view =: news_rownum_news where id_user =: id_user"""
        #select_like_message = cursor.execute(update_rownum,
        #                                        {'news_rownum_news': select_like_message, 'id_user': id_user})
        #conn.commit()
        records = main.cursor.execute(select_like_message, ).fetchall()
        print(records)
        await message.answer(f'{records[3]}\n {records[1]} - {records[2]}\n{records[4]}')
        await asyncio.sleep(10)
    
    #SELECT group_name from users where id_user = 411892636
#-  
async def send_like_message_off(message: Message):
    """Отключение функции оправки упоминаний

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    search_like_message=False
    await message.answer('Функция send_like_message - отключена!')
    
async def time_sleep_notifications(message: Message):
    """Отправка уведомлений о парах перед пар ними 

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    flag_time_sleep = True
    bot = Bot(main.TOKEN, parse_mode="html")
    await message.answer('Функция уведомления - запущена!')
    # Делаем пока пользователь хочет получать уведомления
    while flag_time_sleep == True:
        select_time_sleep_sql = """SELECT id_user,group_name,FIO,notifications from users"""
        select_time_sleep = main.cursor.execute(select_time_sleep_sql, ).fetchall()
        #print(select_time_sleep)
        for j in range(0, len(select_time_sleep)):
            str_select_time_sleep = select_time_sleep[j][3]
            if str_select_time_sleep is None:
                continue
            for time_sleep_one in str_select_time_sleep.split(','):
                #print(time_sleep_one)
                # Узнаем текущее время, дату и неделю
                date1 = datetime.datetime.now().strftime('%H:%M')
                weeknum = datetime.datetime.now().isocalendar().week % 2
                daynum = datetime.datetime.now().isocalendar().weekday

                text_lesson = None

                group_name = select_time_sleep[j][1]
                # Если пользователь студент

                #Если пользователь студент

                if group_name is not None:
                    #print(group_name)
                    sql = """SELECT number_lesson FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                    num = main.cursor.execute(sql,
                                         {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                    for i in num:
                        # print(i[0])
                        number_l = i[0]
                        date_delta = (int(main.lesson_time[number_l][0:2]) * 60 + int(main.lesson_time[number_l][3:5])) - (
                                int(date1[0:2]) * 60 + int(date1[3:5]))
                        text_lesson = [f'У вас через {time_sleep_one} минут начнется:' if date_delta == int(
                            time_sleep_one) else 'None'][0]

                        # Если пора присылать уведомление
                        if text_lesson != 'None':
                            lesson_sql = """SELECT * from schedule where lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson"""
                            lesson = main.cursor.execute(lesson_sql,
                                                    {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum,
                                                     'number_lesson': number_l}).fetchall()
                            for row in lesson:
                                #print(row)
                                await bot.send_message(select_time_sleep[j][0],
                                              f'{text_lesson}\n'
                                              f'<u><b>{row[1]} пара - {main.lesson_time[row[1]]}</b></u>:\n'
                                              f'<b>Предмет:</b> {row[2]}\n<b>Препод.:</b> {row[4]}\n'
                                              f'<b>Формат: </b>{row[3]}\n<b>Аудитория:</b> {row[5]}')
                            text_lesson = None

                # Если пользователя преподаватель
                else:
                    teachers = select_time_sleep[j][2]
                    #print(teachers)
                    sql = """SELECT DISTINCT (number_lesson) FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                    num = main.cursor.execute(sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                    #print(num)
                    d = {}
                    for i in num:
                        # print(i[0])
                        number_l = i[0]
                        date_delta = (int(main.lesson_time[number_l][0:2]) * 60 + int(main.lesson_time[number_l][3:5])) - (
                                int(date1[0:2]) * 60 + int(date1[3:5]))
                        text_lesson = [f'У вас через {time_sleep_one} минут начнется:' if date_delta == int(
                            time_sleep_one) else 'None'][0]

                        # Если пора присылать уведомление
                        if text_lesson != 'None':
                            lesson_sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson ORDER BY number_lesson"""
                            lesson = main.cursor.execute(lesson_sql,
                                                    {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum,
                                                     'number_lesson': number_l}).fetchall()
                            for row in lesson:
                                key = f"{row[1]} {row[2]}"
                                if key in d:
                                    d[key].append(row[0])
                                else:
                                    d[key] = [row[0]]

                            if lesson:
                                for row in lesson:
                                    key = f"{row[1]} {row[2]}"
                                    if not d[key]:
                                        continue
                                    await bot.send_message(select_time_sleep[j][0],
                                                  f'{text_lesson}\n'
                                                  f'<u><b>{row[1]} пара - {main.lesson_time[row[1]]}:</b></u>\n'
                                                  f'<b>Предмет:</b> {row[2]}\n<b>Группа(ы):</b> {", ".join(d[key])}\n'
                                                  f'<b>Формат:</b> {row[3]}\n<b>Аудитория:</b> {row[5]}')
                                    # print(
                                    #    f'{row[1]} пара - {lesson_time[row[1]]}:\n{row[2]}\n{", ".join(d[key])}\n{row[3]}\n{row[5]}')
                                    d[key] = []
                    text_lesson = None
                # Проверка работоспособности
                #print(f"Итерация - {select_time_sleep[j][0]} ---- {text_lesson} --- {time_sleep_one}")
        await asyncio.sleep(60)

#-
# Сделать запросы раз в сутки, путем добавления все в переменные, для оптимизации
async def time_sleep_notifications_add(time_sleep, message: Message, state: FSMContext):
    """Включение уведомлений для пользователя и задание времени оповещения

    Args:
        time_sleep (_type_): Время до начала пар за которое он хочет получить уведомления 
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    print("Нужная мне инфа")
    print(state)
    print("Нужная мне инфа кончилась")
    try:

        test_time_sleep = int(time_sleep)
        str_select_time_sleep = time_sleep

        text_lesson = None
        select_time_sleep_sql = """SELECT notifications from users where id_user =: id_user"""
        select_time_sleep = main.cursor.execute(select_time_sleep_sql, [message.from_user.id]).fetchall()
        if select_time_sleep[0][0] is None:
            update_time_sleep_sql = """UPDATE users SET notifications =: notifications where id_user =: id_user"""
            data_tuple = {'notifications': time_sleep, 'id_user': message.from_user.id}
            main.cursor.execute(update_time_sleep_sql, data_tuple)
            main.conn.commit()
        else:
            for select_time in select_time_sleep:
                str_select_time_sleep = str(select_time[0]) + ',' + str(str_select_time_sleep)
            update_time_sleep_sql = """UPDATE users SET notifications =: notifications where id_user =: id_user"""
            data_tuple = {'notifications': str_select_time_sleep, 'id_user': message.from_user.id}
            main.cursor.execute(update_time_sleep_sql, data_tuple)
            main.conn.commit()


        await message.answer(f'Уведомления за {time_sleep} минут успешно подключены')
        await state.clear()

    except:
        await state.clear()
        await message.answer('Вы не правильно ввели количество минут, попробуйте еще раз')
