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









""" 
Есть мысль  о потенциальной проблеме если много пользователей вызовут эту функцию 
возможно нужно сделать проверку кем является пользователь админ или же просто пользователь 
Так как если сразу несколько пользователей запустят эту функцию бот может лечь  в теории 
"""
# +
async def vk_groups(message):
    """_summary_
    Добавляет новые записи в базу  данных starostat_news c интервалом в 1 час
    Args:
        message (_type_): содержит всю информацию о сообщении отправленном пользователе и о том кто отправил сообщение 
        время ,имя , какой id чата, лучше будет посмотриеть всю эту инфу самому если будет необходиомость работать с ним
    """
    #Авторизация
    vk_session = VkApi(config.login, config.password, auth_handler=interaction_inside.auth_handler)
    vk_session.auth()
    vk = vk_session.get_api()
    #Список с группами, откуда брать информацию
    owner = ['-179693938','470321723','-3375573','-1164947','-181129762']
    #Словарь с источником и его именем
    author = {'-179693938': 'СТИ НИТУ "МИСиС"','470321723': 'Директор','-3375573': 'ГСС','-1164947': 'ФСС','-181129762': 'СМУ'}
    texts = []
    texts_m = []
    #Проверка записей в группах с интервалом в 1 час
    time_zone = 10800
    await message.answer ('Функция вк группы - запущена')
    while True:
        #Проходит по списку групп
        for i in owner:
            check_id_sql = """SELECT date_news, time_news from starostat_news where origin_source = :idd"""
            record = main.cursor.execute(check_id_sql, [i]).fetchall()
            posts = vk.wall.get(owner_id=i, count=3)['items']
            posts_strings = [post['text'] for post in posts]
            posts_time = [post['date'] for post in posts]


            #Счетчики для подсчета новостей и правильной выборке времени
            global сount, count_news
            count = 0
            count_news = 0


            # Делаем перекодировку, так как смайлики в постах вызывают ошибку
            for post in posts_strings:
                text_one = post.split(" ")
                text = " ".join(text_one).encode('cp1251', 'ignore').decode('cp1251', 'ignore')
                texts.append(text)
            
            #Добавление к абсолюдному времени поста  ещё +3 часа по мск
            for text in texts:
                time = datetime.datetime.utcfromtimestamp(posts_time[count]+time_zone)
                time_news = time.strftime('%H:%M:%S')
                date_news = time.strftime("%d.%m.%y")
                # print((post.encode('cp1251', 'ignore').decode('cp1251', 'ignore')))

                msg = vk.wall.get(owner_id=i, count=3)['items'][count]
                
                #Проверка пересылка поста или это личный пост человека
                try:
                    #print('\n---------------------------------------------------------------------------------\n',
                    #      'Пересылка\n')
                    url = await main.getAttachments(msg['copy_history'][0],vk)
                    url = '\n' + url['link'] + '\n'
                    posts_copy_history = msg['copy_history'][0]
                    posts_strings = posts_copy_history['text']
                    text_one = posts_strings.split(" ")
                    text = " ".join(text_one).encode('cp1251', 'ignore').decode('cp1251', 'ignore')
                    text = text + url

                except:
                    #print('\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n',
                    #      'Личный пост\n')
                    url = await main.getAttachments(msg,vk)
                    url = '\n' + url['link'] + '\n'
                    text = text + url
                    #Если будет необходимов вытягивать каждую фотку, то раскоментировать код и список возвращать
                    # for ur in url_m:
                    #     url = '\n' + ur['link'] + '\n'
                    #     text = text + url
                #Проверяем есть ли в базе запись с аналогичным временем и днем
                for rec in record:
                    if rec[0] == date_news and time_news == rec[1]:
                        count_news = count_news + 1


                if count_news > 0 or text is None or text == '':
                    pass
                    #print('Новсть уже есть в базе','---','Пустой пост','---','Пересылка')
                else:
                    id_news_table = """SELECT id_news from starostat_news """
                    records = main.cursor.execute(id_news_table, ).fetchall()
                    id_news = int(records[-1][-1]) + 1
                    sqlite_insert_with_param = """INSERT INTO starostat_news
                                          (id_news, date_news, time_news, author, text, origin_source)
                                          VALUES (:id_news, :date_news, :time_news, :author, :text, :idd)"""

                    authors = author[i]
                    data_tuple = {'id_news': int(id_news), 'date_news': date_news, 'time_news': time_news,
                                  'author': authors, 'text': text, 'idd': i}
                    main.cursor.execute(sqlite_insert_with_param, data_tuple)
                    main.conn.commit()
                    #print(f"Переменные Python {data_tuple} успешно вставлены в таблицу startostat_news")
                count_news = 0
                count = count + 1
            texts = []

        await asyncio.sleep(3600) #Запускаем раз в час


# -
async def insert_varible_into_table_group(id_user, group_name, message: Message):
    """Добавляет новых пользователей в БД как учеников

    Args:
        id_user (_type_): id пользователя в телеграмме 
        group_name (_type_):Название группы (пример ИТ-20-1д)
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """
    try:
        sqlite_insert_with_param = """INSERT INTO users
                              (id_user, group_name)
                              VALUES (:id_user, :group_name)"""
        data_tuple = {'id_user': id_user, 'group_name': group_name}
        main.cursor.execute(sqlite_insert_with_param, data_tuple)
        main.conn.commit()
        print("Переменные Python успешно вставлены в таблицу users")
        await message.answer('Поздравляем с регистрацией!', reply_markup=main.markup_main)
    except cx_Oracle.Error as error:
        print("Ошибка при работе с Oracle", error)

# -
async def insert_varible_into_table_teacher(id_user, FIO, message: Message):
    """Добавляет новых пользователей в БД как преподователей 

    Args:
        id_user (_type_): id пользователя в телеграмме 
        FIO (_type_): ФИО преподователя 
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    try:
        sqlite_insert_with_param = """INSERT INTO users
                              (id_user, FIO)
                              VALUES (:id_user, :FIO)"""
        data_tuple = {'id_user': id_user, 'FIO': FIO}
        main.cursor.execute(sqlite_insert_with_param, data_tuple)
        main.conn.commit()
        await message.answer('Поздравляем с регистрацией!', reply_markup=main.markup_main)
        print("Переменные Python успешно вставлены в таблицу users")

    except cx_Oracle.Error as error:
        print("Ошибка при работе с SQLite", error)

# -
async def read_lesson_teacher(id_user, daynum, weeknum, message: Message):
    """Получение из БД пар для преподавателя и вывод пользователю в сообщении

    Args:
        id_user (_type_): id пользователя в телеграмме 
        daynum (_type_): День недели 
        weeknum (_type_): Числитель или знаменатель
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    group_name_users = """SELECT lower(FIO) from users where id_user =: id_user"""
    records = main.cursor.execute(group_name_users, [id_user]).fetchall()
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
        for row in num:
            key = f"{row[1]} {row[2]}"
            if not d[key]:
                continue
            await message.answer(
                f'<u><b>{row[1]} пара - {main.lesson_time[row[1]]}:</b></u>\n'
                f'<b>Предмет:</b> {row[2]}\n<b>Группа(ы):</b> {", ".join(d[key])}\n'
                f'<b>Формат:</b> {row[3]}\n<b>Аудитория:</b> {row[5]}')
            #print(f'{row[1]} пара - {lesson_time[row[1]]}:\n{row[2]}\n{", ".join(d[key])}\n{row[3]}\n{row[5]}')
            d[key] = []

        # bot.send_message(message.chat.id, f"http://r.sf-misis.ru/teacher/{num[0][0]}")
    else:
        daynum_schedule = ['понедельник' if daynum == 1 else ('вторник' if daynum == 2 else (
            'среду' if daynum == 3 else ('четверг' if daynum == 4 else (
                'пятницу' if daynum == 5 else ('субботу' if daynum == 6 else ('воскресенье'))))))]
        week_schedule = ['числителю' if weeknum == 0 else ('знаменателю')]
        await message.answer(f'У вас в {daynum_schedule[0]} по {week_schedule[0]} нет пар!')

# -
async def read_lesson(id_user, daynum, weeknum, message: Message):
    """Получение из БД пар для студентов и вывод пользователю в сообщении

    Args:
        id_user (_type_): id пользователя в телеграмме 
        daynum (_type_): День недели 
        weeknum (_type_): Числитель или знаменатель
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    group_name_users = """SELECT group_name from users where id_user =: id_user"""
    records = main.cursor.execute(group_name_users, [id_user]).fetchall()
    group_name = records[0][0]
    sql = """SELECT * FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
    num = main.cursor.execute(sql, {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
    #print(records[0][0], daynum, weeknum)
    if num:
        for row in num:
            #print(row)
            await message.answer(
                f'<u><b>{row[1]} пара - {main.lesson_time[row[1]]}</b></u>:\n'
                f'<b>Предмет:</b> {row[2]}\n<b>Препод.:</b> {row[4]}\n'
                f'<b>Формат: </b>{row[3]}\n<b>Аудитория:</b> {row[5]}')
            # bot.send_message(message.chat.id, f"http://r.sf-misis.ru/group/{num[0][0]}")
    else:
        daynum_schedule = ['понедельник' if daynum == 1 else ('вторник' if daynum == 2 else (
            'среду' if daynum == 3 else ('четверг' if daynum == 4 else (
                'пятницу' if daynum == 5 else ('субботу' if daynum == 6 else ('воскресенье'))))))]
        week_schedule = ['числителю' if weeknum == 0 else ('знаменателю')]
        await message.answer(f'У вас в {daynum_schedule[0]} по {week_schedule[0]} нет пар!')



#-
async def news(id_user, message: Message,type):
    """Функция для получения из бд новостей по теме которую запросил пользователь и вывода их пользователю 

    Args:
        id_user (_type_): id пользователя в телеграмме 
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        type (_type_): Тип новости который запросил пользователь из старостата , групп вк или же по трудоустройству
    """    
    news_rownum_sql = """SELECT id_news from starostat_news"""
    rownum_sql = main.cursor.execute(news_rownum_sql, ).fetchall()
    end_news = int(len(rownum_sql))

    if(type[-2:]=='05'):
        len_news=5
        print(type[-2:])
    else:
        len_news=10

    print("ID user:", id_user)
    #Если пришет что всё уже просмотренно но ничего не смотрел то надо запустить без 
    if(type[:-2]=='starostat'):
        news_news_sql = f"""SELECT * from starostat_news  where id_news in ( select id_news
from (select INSTR(b.news_view, a.id_news) as newss, b.news_view, a.id_news from starostat_news a, users b where id_user = {id_user} and (origin_source is null )) a
where (a.newss = 0 or a.newss is null) and rownum <= {len_news} )"""
    elif(type[:-2]=='group'):
        news_news_sql = f"""  SELECT * from starostat_news  where id_news in ( select id_news
from (select INSTR(b.news_view, a.id_news) as newss, b.news_view, a.id_news from starostat_news a, users b where id_user = 411892636 and (a.origin_source = -179693938 
or origin_source='-181129762'or origin_source='-1164947' or origin_source='-3375573' or origin_source='470321723' )) a
where (a.newss = 0 or a.newss is null) and  rownum <= {len_news} ) """
    elif(type[:-2]=='job'):
        news_news_sql = f"""SELECT * from starostat_news  where id_news in ( select id_news
from (select INSTR(b.news_view, a.id_news) as newss, b.news_view, a.id_news from starostat_news a, users b where id_user = {id_user} and (text like '%трудоустройств%' )) a
where (a.newss = 0 or a.newss is null) and rownum <= {len_news} )"""
    
    
    records = main.cursor.execute(news_news_sql, ).fetchall()

    news_rownum_user_news_view = """SELECT news_view from users where id_user =: id_user"""
    news_rownum = main.cursor.execute(news_rownum_user_news_view, [id_user]).fetchall()
    count = 0
    for x in records:
        print(x)
    
    for row in news_rownum:
        news_rownum_news = str(row[0])
        
    for i in records:
        print (i)
        news_rownum_count = news_rownum_news.split(',')
        test_1 = str(i[4]).split(' ')
        print(str(test_1[0]) not in news_rownum_count)

        if str(test_1[0]) not in news_rownum_count:
            print(str(i[0]))
            
            news_rownum_news = news_rownum_news + ',' + str(i[0])
            update_rownum = """UPDATE users SET news_view =: news_rownum_news where id_user =: id_user"""
            update_rownum_news = main.cursor.execute(update_rownum,
                                                {'news_rownum_news': news_rownum_news, 'id_user': id_user})
            main.conn.commit()
            await message.answer(f'{i[3]}\n {i[1]} - {i[2]}\n{i[4]}')
            count = count + 1
    if count == 0:
        await message.answer(f'Вы все просмотрели, новых сообщений нет!')

#-
async def news_all(id_user):
    """Функция для получения из бд всех новостей  (не используется сейчас)

    Args:
        id_user (_type_): id пользователя в телеграмме
    """   
    news_rownum_user = """SELECT news_view from users"""
    news_rownum = main.cursor.execute(news_rownum_user, ).fetchall()
    mews = news_rownum[0][0]
    news_news_user = """SELECT date_news, time_news, author, text from starostat_news where id_news <>: mews"""
    news_news = main.cursor.execute(news_news_user, [mews]).fetchall()
    #print(news_news)

    # builder_i = [
    #     [InlineKeyboardButton(text='ПН', callback_data='ss'), InlineKeyboardButton(text='ВТ', callback_data='sdsa'),
    #      InlineKeyboardButton(text='СР', callback_data='sdsa'), InlineKeyboardButton(text='ЧТ', callback_data='sdsa'),
    #      InlineKeyboardButton(text='ПТ', callback_data='sdsa'), InlineKeyboardButton(text='СБ', callback_data='sdsa')]]
    # keyboard1 = InlineKeyboardMarkup(inline_keyboard=builder_i)
    # await message.answer("Как подавать котлеты?", reply_markup=keyboard1)
#-
async def lk(message: Message):
    """Личный кабинет получение информации о пользователе из бд и вывод это информации на экран 

    Args:
        message (Message):  сообщение из которого можно достать всю инфу о пользователе
    """    
    group_name_users = """SELECT group_name from users where id_user =: id_user"""
    records = main.cursor.execute(group_name_users, [message.from_user.id]).fetchall()
    if records[0][0] != None:
        group_name_users = """SELECT group_name, notifications from users where id_user =: id_user"""
        records = main.cursor.execute(group_name_users, [message.from_user.id]).fetchall()
        group_name = records[0][0]
        notifications = [f'за {records[0][1]} минуты' if records[0][1] != None else 'не подключены']
        await message.answer(f'Профиль: студент\n'
                             f'Группа: {group_name}\n'
                             f'Подгруппа: \n'
                             f'Уведомления: {notifications[0]}\n\n'
                             f'Для сброса аккаунта можно использовать /delete')
    else:
        group_name_users = """SELECT FIO, notifications from users where id_user =: id_user"""
        records = main.cursor.execute(group_name_users, [message.from_user.id]).fetchall()
        FIO = records[0][0]
        notifications = [f'за {records[0][1]} минуты' if records[0][1] != None else 'не подключены']
        await message.answer(f'Профиль: преподаватель\n'
                             f'ФИО: {FIO}\n'
                             f'Уведомления: {notifications[0]}\n\n'
                             f'Для сброса аккаунта можно использовать /delete')
