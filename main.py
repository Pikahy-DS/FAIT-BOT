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

form_router = Router()

class Form(StatesGroup):
    type_group_teacher = State()
    name = State()
    time_sleep_notifications = State()


TOKEN = config.TOKEN
dp = Dispatcher(storage=MemoryStorage())
conn = cx_Oracle.connect('hr/hr2020@ORCLPDB')
cursor = conn.cursor()
logger = logging.getLogger(__name__)
owm = pyowm.OWM(config.TOKEN_OWM)

lesson_time = {1: '09:00-10:30',
               2: '10:40-12:10',
               3: '12:40-14:10',
               4: '14:20-15:50',
               5: '16:00-17:30',
               6: '18:30-20:00',
               7: '20:10-21:40'}


builder_main = [[KeyboardButton(text='Расписание'),
                 KeyboardButton(text='Новости'),
                 KeyboardButton(text = 'Уведомления')],
                [KeyboardButton(text='Профиль')]]
markup_main = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_main)
builder_main_admin = [[KeyboardButton(text='Расписание'),
                 KeyboardButton(text='Новости'),
                 KeyboardButton(text = 'Уведомления')],
                [KeyboardButton(text='Профиль')],[
                 KeyboardButton(text = 'Запуск погоды'),
                 KeyboardButton(text = '🛎 Запуск уведомлений'),
                 KeyboardButton(text = 'Запуск вк групп'),
                 KeyboardButton(text='Запуск склейки')]]
markup_main_admin = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_main_admin)
#+
def _today():                                                     # функция для определения сегодняшнего дня недели          
    """Функция для определения дня недели и знаминателя числителя

    Returns:
        string: Возвращает день недели и числитель  или знаменатель в формате 
        Сегодня  понедельник, знаменатель
    """
    day_number = datetime.datetime.now().isocalendar()[2]          # определения номера дня недели
    week_number = datetime.datetime.now().isocalendar()[1]%2          # определяем четность номера недели

    # записываем в строку день недели
    if day_number == 1:                                                                     
        day_string = 'понедельник'
    elif day_number == 2:
        day_string = 'вторник'
    elif day_number == 3:
        day_string = 'среда'
    elif day_number == 4:
        day_string = 'четверг'
    elif day_number == 5:
        day_string = 'пятница'
    elif day_number == 6:
        day_string = 'суббота'
    elif day_number == 7:
        day_string = 'воскресенье'
    
    # записываем в строку числитель или знаменатель в зависимости от четности номера недели
    if week_number == 0:
        week_string = 'числитель'
    elif week_number == 1:
        week_string = 'знаменатель'

    today_string = ('Сегодня ' + day_string + ', ' + week_string)     # записываем все в одну строку

    return today_string                 # возвращаем строку
#-
async def auth_handler():
    
    """
    Обработчик двухфакторной аутентификации (если включена) 
    Returns:
        _type_: _description_
    """
    key = input('Enter authentication code: ')
    return key, True

# + - 
async def getAttachments(msg, vk):
    """Получение фото из  поста  но это не точно надо будет ещё с этой функций разобраться 

    Args:
        msg (_type_): _description_
        vk (_type_): _description_

    Returns:
        _type_: _description_
    """    
    attachList = []

    for att in msg['attachments'][0:]:

        attType = att.get('type')

        attachment = att[attType]

        if attType == 'photo':  # Проверка на тип фотографии

            for photoType in attachment.get('sizes')[0:]:
                if photoType.get('type') == 'x':  # <=604x604
                    attachments = photoType.get('url')
                if photoType.get('type') == 'y':  # >605x605
                    attachments = photoType.get('url')
                if photoType.get('type') == 'z':  # <=1280x720
                    attachments = photoType.get('url')
                if photoType.get('type') == 'w':  # >1280x720
                    attachments = photoType.get('url')  # <=2560x1440
                    attType = 'other'

        elif attType == 'doc':  # Проверка на тип документа:
            # Про типы документов можно узнать тут: https://vk.com/dev/objects/doc
            docType = attachment.get('type')
            if docType != 3 and docType != 4 and docType != 5:
                attType = 'other'
            if attachment.get('url'):
                attachments = attachment.get('url')

        elif attType == 'sticker':  # Проверка на стикеры:
            for sticker in attachment.get('images')[0:]:
                # Можно 256 или 512, но будет слишком огромная пикча
                if sticker.get('width') == 128:
                    attachments = sticker.get('url')

        elif attType == 'audio':
            attachments = str('𝅘𝅥𝅮 ' + attachment.get('artist') + ' - ' +
                              attachment.get('title') + ' 𝅘𝅥𝅮')
            attType = 'other'

        elif attType == 'audio_message':
            attachments = attachment.get('link_ogg')

        elif attType == 'video':

            ownerId = str(attachment.get('owner_id'))
            videoId = str(attachment.get('id'))
            accesskey = str(attachment.get('access_key'))

            fullURL = str(ownerId + '_' + videoId + '_' + accesskey)

            attachments = vk.video.get(videos=fullURL)['items'][0].get('player')

        elif attType == 'graffiti':
            attType = 'other'
            attachments = attachment.get('url')

        elif attType == 'link':
            attType = 'other'
            attachments = attachment.get('url')

        elif attType == 'wall':
            attType = 'other'
            attachments = 'https://vk.com/wall'
            from_id = str(attachment.get('from_id'))
            post_id = str(attachment.get('id'))
            attachments += from_id + '_' + post_id

        elif attType == 'wall_reply':
            attType = 'other'
            attachments = 'https://vk.com/wall'
            owner_id = str(attachment.get('owner_id'))
            reply_id = str(attachment.get('id'))
            post_id = str(attachment.get('post_id'))
            attachments += owner_id + '_' + post_id
            attachments += '?reply=' + reply_id

        elif attType == 'poll':
            attType = 'other'
            attachments = 'https://vk.com/poll'
            owner_id = str(attachment.get('owner_id'))
            poll_id = str(attachment.get('id'))
            attachments += owner_id + '_' + poll_id
        # Неизвестный тип?
        else:

            attachments = None

        attachList.append({'type': attType,
                           'link': attachments})

    # print( attachList )

    return attachList[0]

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
    vk_session = VkApi(config.login, config.password, auth_handler=auth_handler)
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
            record = cursor.execute(check_id_sql, [i]).fetchall()
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
                    url = await getAttachments(msg['copy_history'][0],vk)
                    url = '\n' + url['link'] + '\n'
                    posts_copy_history = msg['copy_history'][0]
                    posts_strings = posts_copy_history['text']
                    text_one = posts_strings.split(" ")
                    text = " ".join(text_one).encode('cp1251', 'ignore').decode('cp1251', 'ignore')
                    text = text + url

                except:
                    #print('\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n',
                    #      'Личный пост\n')
                    url = await getAttachments(msg,vk)
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
                    records = cursor.execute(id_news_table, ).fetchall()
                    id_news = int(records[-1][-1]) + 1
                    sqlite_insert_with_param = """INSERT INTO starostat_news
                                          (id_news, date_news, time_news, author, text, origin_source)
                                          VALUES (:id_news, :date_news, :time_news, :author, :text, :idd)"""

                    authors = author[i]
                    data_tuple = {'id_news': int(id_news), 'date_news': date_news, 'time_news': time_news,
                                  'author': authors, 'text': text, 'idd': i}
                    cursor.execute(sqlite_insert_with_param, data_tuple)
                    conn.commit()
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
        cursor.execute(sqlite_insert_with_param, data_tuple)
        conn.commit()
        print("Переменные Python успешно вставлены в таблицу users")
        await message.answer('Поздравляем с регистрацией!', reply_markup=markup_main)
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
        cursor.execute(sqlite_insert_with_param, data_tuple)
        conn.commit()
        await message.answer('Поздравляем с регистрацией!', reply_markup=markup_main)
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
    records = cursor.execute(group_name_users, [id_user]).fetchall()
    teachers = records[0][0]
    sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
    num = cursor.execute(sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
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
                f'<u><b>{row[1]} пара - {lesson_time[row[1]]}:</b></u>\n'
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
    records = cursor.execute(group_name_users, [id_user]).fetchall()
    group_name = records[0][0]
    sql = """SELECT * FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
    num = cursor.execute(sql, {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
    #print(records[0][0], daynum, weeknum)
    if num:
        for row in num:
            #print(row)
            await message.answer(
                f'<u><b>{row[1]} пара - {lesson_time[row[1]]}</b></u>:\n'
                f'<b>Предмет:</b> {row[2]}\n<b>Препод.:</b> {row[4]}\n'
                f'<b>Формат: </b>{row[3]}\n<b>Аудитория:</b> {row[5]}')
            # bot.send_message(message.chat.id, f"http://r.sf-misis.ru/group/{num[0][0]}")
    else:
        daynum_schedule = ['понедельник' if daynum == 1 else ('вторник' if daynum == 2 else (
            'среду' if daynum == 3 else ('четверг' if daynum == 4 else (
                'пятницу' if daynum == 5 else ('субботу' if daynum == 6 else ('воскресенье'))))))]
        week_schedule = ['числителю' if weeknum == 0 else ('знаменателю')]
        await message.answer(f'У вас в {daynum_schedule[0]} по {week_schedule[0]} нет пар!')

# -
async def schedule(id_user, daynum, weeknum, message: Message):
    """Определение студент или преподователь и запуск соответствующей функции для вывода

    Args:
        id_user (_type_): id пользователя в телеграмме 
        daynum (_type_): День недели 
        weeknum (_type_): Числитель или знаменатель
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    try:
        group_name_users = """SELECT group_name from users where id_user =: id_user"""
        records = cursor.execute(group_name_users, [id_user]).fetchall()
        if records[0][0] != None:
            await read_lesson(id_user, daynum, weeknum, message)
        else:
            await read_lesson_teacher(id_user, daynum, weeknum, message)
    except:
        await message.answer('Ошибка, введите команду /start')


# склейка новостей
#   --- 
async def update_news_table(message: Message):
    """склейка новостей

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
    await message.answer ("Функция склейка новостей - запущена")
    flag = True
    while True:
        news_count = 0
        while flag:
            news_rownum_sql = """SELECT id_news, date_news, time_news, author, text from starostat_news"""
            rownum_sql = cursor.execute(news_rownum_sql, ).fetchall()
            #print(rownum_sql[0])
            count = 0
            for i in range(1, len(rownum_sql)):
                if rownum_sql[i][1] == rownum_sql[i - 1][1] and rownum_sql[i][2][0:5] == rownum_sql[i - 1][2][0:5] and rownum_sql[i - 1][3] == rownum_sql[i][3] and (len(rownum_sql[i][4].encode('utf-8'))+len(rownum_sql[i-1][4].encode('utf-8'))) < 4000:
                    #print(len(rownum_sql[i-1][4].encode('utf-8')), ' -------------------------', len(rownum_sql[i][4].encode('utf-8')))
                    update_table_str = """UPDATE starostat_news SET text =: text  where id_news =: id_news"""
                    text = rownum_sql[i - 1][4] + '\n' + rownum_sql[i][4]
                    id_news = rownum_sql[i - 1][0]
                    update_table_dict = {'text': text, 'id_news': id_news}
                    update_table = cursor.execute(update_table_str, update_table_dict)
                    conn.commit()
                    id_news_d = rownum_sql[i][0]
                    delete_table_str = """DELETE FROM starostat_news where id_news =: id_news_d"""
                    delete_table = cursor.execute(delete_table_str, [id_news_d])
                    conn.commit()
                    #print('успешно: ', rownum_sql[i - 1][4] + '\n' + rownum_sql[i][4], ' ', [rownum_sql[i][0]])
                    news_count = news_count + 1
                    break
                else:
                    count = count + 1
                    # print(rownum_sql[i-1][2][0:5],int(rownum_sql[i-1][2][3:5])-1)
                    if count == len((rownum_sql)) - 1:
                        flag = False
        if news_count > 0:
            pass
            #await message.answer(f'Успешно склеено {news_count} новости(ей)')
        else:
            pass
            #await message.answer("Отсутствуют новости для склеивания")
        await asyncio.sleep(60)
#news(message.from_user.id, message)

#-
async def news(id_user, message: Message,type):
    """Функция для получения из бд новостей по теме которую запросил пользователь и вывода их пользователю 

    Args:
        id_user (_type_): id пользователя в телеграмме 
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        type (_type_): Тип новости который запросил пользователь из старостата , групп вк или же по трудоустройству
    """    
    news_rownum_sql = """SELECT id_news from starostat_news"""
    rownum_sql = cursor.execute(news_rownum_sql, ).fetchall()
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
    
    
    records = cursor.execute(news_news_sql, ).fetchall()

    news_rownum_user_news_view = """SELECT news_view from users where id_user =: id_user"""
    news_rownum = cursor.execute(news_rownum_user_news_view, [id_user]).fetchall()
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
            update_rownum_news = cursor.execute(update_rownum,
                                                {'news_rownum_news': news_rownum_news, 'id_user': id_user})
            conn.commit()
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
    news_rownum = cursor.execute(news_rownum_user, ).fetchall()
    mews = news_rownum[0][0]
    news_news_user = """SELECT date_news, time_news, author, text from starostat_news where id_news <>: mews"""
    news_news = cursor.execute(news_news_user, [mews]).fetchall()
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
    records = cursor.execute(group_name_users, [message.from_user.id]).fetchall()
    if records[0][0] != None:
        group_name_users = """SELECT group_name, notifications from users where id_user =: id_user"""
        records = cursor.execute(group_name_users, [message.from_user.id]).fetchall()
        group_name = records[0][0]
        notifications = [f'за {records[0][1]} минуты' if records[0][1] != None else 'не подключены']
        await message.answer(f'Профиль: студент\n'
                             f'Группа: {group_name}\n'
                             f'Подгруппа: \n'
                             f'Уведомления: {notifications[0]}\n\n'
                             f'Для сброса аккаунта можно использовать /delete')
    else:
        group_name_users = """SELECT FIO, notifications from users where id_user =: id_user"""
        records = cursor.execute(group_name_users, [message.from_user.id]).fetchall()
        FIO = records[0][0]
        notifications = [f'за {records[0][1]} минуты' if records[0][1] != None else 'не подключены']
        await message.answer(f'Профиль: преподаватель\n'
                             f'ФИО: {FIO}\n'
                             f'Уведомления: {notifications[0]}\n\n'
                             f'Для сброса аккаунта можно использовать /delete')
#-
async def weather(message: Message):
    """Функция  рассылки погоды и пар 

    Args:
        message (Message):  сообщение из которого можно достать всю инфу о пользователе
    """    
    flag_time_sleep = True
    await message.answer('Функция погода - запущена')
    bot = Bot(TOKEN, parse_mode="html")
    while flag_time_sleep:
        #message.answer
        date1 = datetime.datetime.now().strftime('%H:%M')
        if date1[0:2] == '8' and date1[3:5] == '00':
            weeknum = datetime.datetime.now().isocalendar()[2] % 2
            daynum = datetime.datetime.now().isocalendar()[2]
            
            select_weather_schedule_sql = """SELECT id_user from users"""
            select_weather_schedule = cursor.execute(select_weather_schedule_sql, ).fetchall()
            for i in select_weather_schedule:
                
                #print(i[0])
                group_name_users = """SELECT group_name from users where id_user =: id_user"""
                records = cursor.execute(group_name_users, [i[0]]).fetchall()
                if records[0][0] != None:
                    group_name = records[0][0]
                    sql = """SELECT * FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                    num = cursor.execute(sql,
                                         {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                    
                    #print(records[0][0], daynum, weeknum)
                    #try и except в этом случае нужен для того что бы при остсутствии чата с человеком но 
                    # наличии его в базе данных пропустить его и не вызывать ошибку прирывая исполнение кода 
                    if num:
                        
                        try:
                            await bot.send_message(i[0],f'Доброе утро! Ваши пары на сегодня:\n')
                        except:
                            continue
                        for row in num:
                            
                            #print(row)
                            await bot.send_message(i[0],
                                                   f'<u><b>{row[1]} пара - {lesson_time[row[1]]}</b></u>:\n'
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
                    records = cursor.execute(group_name_users, [i[0]]).fetchall()
                    teachers = records[0][0]
                    sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                    num = cursor.execute(sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
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
                                                   f'<u><b>{row[1]} пара - {lesson_time[row[1]]}:</b></u>\n'
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
                    mgr = owm.weather_manager()
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
    select_time_sleep = cursor.execute(select_time_sleep_sql, [message.chat.id]).fetchall()
    #print(message.chat.id)
    update_time_sleep_sql = """UPDATE users SET notifications =: notifications where id_user =: id_user"""
    data_tuple = {'notifications': str_select_time_sleep, 'id_user': message.chat.id}
    cursor.execute(update_time_sleep_sql, data_tuple)
    conn.commit()
    #print('Успешно удалены', '====', str_select_time_sleep)

#Функция отправки сообщений  при упоминании
#-
async def send_like_message(message: Message):
    """Функция отправки сообщений  при упоминании 

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
    """    
       
    bot = Bot(TOKEN, parse_mode="html")
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
        records = cursor.execute(select_like_message, ).fetchall()
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
    bot = Bot(TOKEN, parse_mode="html")
    await message.answer('Функция уведомления - запущена!')
    # Делаем пока пользователь хочет получать уведомления
    while flag_time_sleep == True:
        select_time_sleep_sql = """SELECT id_user,group_name,FIO,notifications from users"""
        select_time_sleep = cursor.execute(select_time_sleep_sql, ).fetchall()
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
                    num = cursor.execute(sql,
                                         {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                    for i in num:
                        # print(i[0])
                        number_l = i[0]
                        date_delta = (int(lesson_time[number_l][0:2]) * 60 + int(lesson_time[number_l][3:5])) - (
                                int(date1[0:2]) * 60 + int(date1[3:5]))
                        text_lesson = [f'У вас через {time_sleep_one} минут начнется:' if date_delta == int(
                            time_sleep_one) else 'None'][0]

                        # Если пора присылать уведомление
                        if text_lesson != 'None':
                            lesson_sql = """SELECT * from schedule where lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson"""
                            lesson = cursor.execute(lesson_sql,
                                                    {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum,
                                                     'number_lesson': number_l}).fetchall()
                            for row in lesson:
                                #print(row)
                                await bot.send_message(select_time_sleep[j][0],
                                              f'{text_lesson}\n'
                                              f'<u><b>{row[1]} пара - {lesson_time[row[1]]}</b></u>:\n'
                                              f'<b>Предмет:</b> {row[2]}\n<b>Препод.:</b> {row[4]}\n'
                                              f'<b>Формат: </b>{row[3]}\n<b>Аудитория:</b> {row[5]}')
                            text_lesson = None

                # Если пользователя преподаватель
                else:
                    teachers = select_time_sleep[j][2]
                    #print(teachers)
                    sql = """SELECT DISTINCT (number_lesson) FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                    num = cursor.execute(sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                    #print(num)
                    d = {}
                    for i in num:
                        # print(i[0])
                        number_l = i[0]
                        date_delta = (int(lesson_time[number_l][0:2]) * 60 + int(lesson_time[number_l][3:5])) - (
                                int(date1[0:2]) * 60 + int(date1[3:5]))
                        text_lesson = [f'У вас через {time_sleep_one} минут начнется:' if date_delta == int(
                            time_sleep_one) else 'None'][0]

                        # Если пора присылать уведомление
                        if text_lesson != 'None':
                            lesson_sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson ORDER BY number_lesson"""
                            lesson = cursor.execute(lesson_sql,
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
                                                  f'<u><b>{row[1]} пара - {lesson_time[row[1]]}:</b></u>\n'
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
        select_time_sleep = cursor.execute(select_time_sleep_sql, [message.from_user.id]).fetchall()
        if select_time_sleep[0][0] is None:
            update_time_sleep_sql = """UPDATE users SET notifications =: notifications where id_user =: id_user"""
            data_tuple = {'notifications': time_sleep, 'id_user': message.from_user.id}
            cursor.execute(update_time_sleep_sql, data_tuple)
            conn.commit()
        else:
            for select_time in select_time_sleep:
                str_select_time_sleep = str(select_time[0]) + ',' + str(str_select_time_sleep)
            update_time_sleep_sql = """UPDATE users SET notifications =: notifications where id_user =: id_user"""
            data_tuple = {'notifications': str_select_time_sleep, 'id_user': message.from_user.id}
            cursor.execute(update_time_sleep_sql, data_tuple)
            conn.commit()


        await message.answer(f'Уведомления за {time_sleep} минут успешно подключены')
        await state.clear()

    except:
        await state.clear()
        await message.answer('Вы не правильно ввели количество минут, попробуйте еще раз')

@form_router.message(commands={"cancel"})
@form_router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """ 
    Прирывание шагов какого либо процесса более продобно можно прочитать тут
        https://mastergroosha.github.io/telegram-tutorial-2/fsm/
        в нашем случает это регистрация
       прошлый коммент  Allow user to cancel any action(Разрешить пользователю отменить любое действие)
    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """    
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Cancelled.",
        reply_markup=ReplyKeyboardRemove(),
    )

# Этап регистрации при отсутсвии аккаунта в базе
#-
@form_router.message(Form.type_group_teacher, F.text == "Студент")
async def process_type_group(message: Message, state: FSMContext) -> None:
    """Этап регистрации при отсутсвии аккаунта в базе для студента

    Args:
         message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    await state.update_data(type_group_teacher=message.text)
    #print(message.text)
    await state.set_state(Form.name)
    await message.answer(f"Введите номер группы в формате - 'АТ-18-1д'", reply_markup=ReplyKeyboardRemove())

#-
@form_router.message(Form.type_group_teacher, F.text == "Преподаватель")
async def process_type_teacher(message: Message, state: FSMContext) -> None:
    """Этап регистрации при отсутсвии аккаунта в базе для преподователей

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """  
    User = await state.update_data(type_group_teacher=message.text)
    await state.set_state(Form.name)
    builder_teacher = [
        [KeyboardButton(text='Цыганков Юрий Александрович'), KeyboardButton(text='Соловьев Антон Юрьевич')]]
    markup_teacher = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_teacher)
    await message.answer('Введите ваше ФИО в полном формате.', reply_markup=markup_teacher)


@form_router.message(Form.name)
async def process_name(message: Message, state: FSMContext) -> None:
    """Функция проверки принадлежит ли студент к существующим группам или преподователям и запуск нужной для регистарции

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    User = await state.update_data(name=message.text)
    id_user = message.from_user.id
    if User['type_group_teacher'] == 'Студент':
        student_check_sql = """SELECT group_name from groups where lower(group_name) = lower(:group_name)"""
        student_check = cursor.execute(student_check_sql, [message.text]).fetchall()
        #print(student_check)
        if student_check:
            await insert_varible_into_table_group(id_user, User['name'], message)
            #print(User['name'])
            await state.clear()
        else:
            await message.answer('Вы ввели несуществующую группу, давайте начнем сначала')
            await command_start_handler(message, state)
    else:
        student_check_sql = """SELECT FIO from teachers where lower(FIO) = lower(:FIO)"""
        student_check = cursor.execute(student_check_sql, [message.text]).fetchall()
        #print(student_check)
        if student_check:
            await insert_varible_into_table_teacher(id_user, User['name'], message)
            #print(User['name'])
            await state.clear()
        else:
            await command_start_handler(message, state)
            await message.answer('Вы ввели несуществующего преподавателя, давайте начнем сначала')

@form_router.message(Form.time_sleep_notifications)
async def process_time_sleep_notifications(message: Message, state: FSMContext) -> None:
    """Запуск функций включени уведомления в виде стадий 

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    time_state = await state.update_data(time_sleep_notifications=message.text)
    await time_sleep_notifications_add(time_state['time_sleep_notifications'], message, state)
    await state.clear()

# Обработка инлайн кнопок
@form_router.callback_query(lambda c: c.data)
async def call_handle(call: types.callback_query) -> None:
    """Обработка инлайн кнопок для пользователя (кнопки которые есть в сообщении пользователю)

    Args:
        call (types.callback_query): Ответ который присвоен каждой кнопке и при нажатии на которую вернётся 
        для дальнейшей обработки
    """    
    if call.data == 'monday0':
        #print('one')
        weeknum = 0
        daynum = 1
        name_daynum = 'Понедельник'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по числителю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'tuesday0':
        weeknum = 0
        daynum = 2
        name_daynum = 'Вторник'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по числителю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'wednesday0':
        weeknum = 0
        daynum = 3
        name_daynum = 'Среду'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по числителю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'thrusday0':
        weeknum = 0
        daynum = 4
        name_daynum = 'Четверг'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по числителю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'friday0':
        weeknum = 0
        daynum = 5
        name_daynum = 'Пятницу'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по числителю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'saturday0':
        weeknum = 0
        daynum = 6
        name_daynum = 'Субботу'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по числителю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'monday1':
        weeknum = 1
        daynum = 1
        name_daynum = 'Понедельник'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по знаменателю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'tuesday1':
        weeknum = 1
        daynum = 2
        name_daynum = 'Вторник'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по знаменателю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'wednesday1':
        weeknum = 1
        daynum = 3
        name_daynum = 'Среду'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по знаменателю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'thrusday1':
        weeknum = 1
        daynum = 4
        name_daynum = 'Четверг'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по знаменателю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'friday1':
        weeknum = 1
        daynum = 5
        name_daynum = 'Пятницу'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по знаменателю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'saturday1':
        weeknum = 1
        daynum = 6
        name_daynum = 'Субботу'
        await call.answer(f'Вы выбрали {name_daynum}')
        await call.message.edit_text(f'Пары в {name_daynum} по знаменателю: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'today':
        weeknum = datetime.datetime.now().isocalendar().week % 2
        daynum = datetime.datetime.now().isocalendar().weekday
        await call.answer(f'Вы выбрали пары на сегодня')
        await call.message.edit_text(f'Пары сегодня: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'off_notifications':
        await delete_time_sleep_notifications(call.message)
        await call.answer(f'Все уведомления отключены')
        await call.message.edit_text(f'Все уведомления отключены ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        #Добавить столбец с временами уведомлений и очищать его при нажатии на кнопку, в виде запроса запрашивать время уведомлений.
    elif call.data[:-2] == "starostat":
        await call.message.edit_text(f'Новости из старостата')
        await news(call.from_user.id, call.message,call.data)
    elif call.data[:-2] == "group":
        await call.message.edit_text(f'Новости из группы')
        await news(call.from_user.id, call.message,call.data)
    elif call.data[:-2] == "job":
        await call.message.edit_text(f'Новости по трудоустройству')
        await news(call.from_user.id, call.message,call.data)
    
    else:
        print(call)


async def sleep_test():
    """сейчас не используется 
    """    
    flag = True
    count = 0
    while flag:
        #print(f"Итерация - {count}")

        count = count + 1
        await asyncio.sleep(1)

# Действия при вводе /start
@form_router.message(commands={"start"})
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """Функция начала регастрации пользователя если у него нет аккаунта 
    или же вывод кнопок для взаимодействия людям у которых есть аккаунт 

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    id_user = message.from_user.id
    print(message.from_user.id)
    group_name_users = """SELECT group_name from users where id_user =: id_user"""
    records = cursor.execute(group_name_users, [message.from_user.id]).fetchall()
    #print(records)
    if records:
        if message.from_user.id == 1005179687:
            await message.answer(
                "Привет, {0.first_name}!\nВы находитесь в кабинете администратора. ".format(
                    message.from_user), reply_markup=markup_main_admin)
        else:
            await message.answer(
                "Привет, {0.first_name}!\nЯ - <b>Помошник</b>, бот созданный, чтобы упростить просмотр расписания ".format(
                    message.from_user), reply_markup=markup_main)
    else:
        builder_teacher_group = [[KeyboardButton(text='Студент'), KeyboardButton(text='Преподаватель')]]
        teacher_group = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_teacher_group)
        await state.set_state(Form.type_group_teacher)
        await message.reply('Ты кто?', reply_markup=teacher_group)

# Удаление аакаунта из базы
@form_router.message(commands={"delete"})
async def delete_account(message: Message, state: FSMContext) -> None:
    """Удаление человека из бд 

    Args:
        message (Message): ообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    delete_account_sql = """delete
                          users where id_user = :id_user"""
    id_user = message.from_user.id
    data_tuple = {'id_user': id_user}
    cursor.execute(delete_account_sql, data_tuple)
    conn.commit()
    builder_delete = [[KeyboardButton(text='/start')]]
    markup_delete = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_delete)
    await message.answer('Аккаунт успешно удален')
    await message.answer('Для начала работы с ботом нажмите: /start', reply_markup=markup_delete)

# Обработка текстовых сообщений и обычной клавиатуры
@form_router.message(content_types=['text'])
async def text_button(message: Message, state: FSMContext) -> Any:
    """Обработка текстовых сообщений и обычной клавиатуры

    Args:
        message (Message): ообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах

    Returns:
        Any: _description_
    """    
    if message.text == 'Расписание':
        builder_schedule = [[InlineKeyboardButton(text='ПН', callback_data='monday0'),
                             InlineKeyboardButton(text="ВТ", callback_data='tuesday0'),
                             InlineKeyboardButton(text='СР', callback_data='wednesday0'),
                             InlineKeyboardButton(text='ЧТ', callback_data='thrusday0'),
                             InlineKeyboardButton(text='ПТ', callback_data='friday0'),
                             InlineKeyboardButton(text='СБ', callback_data='saturday0')],
                            [InlineKeyboardButton(text='ПН', callback_data='monday1'),
                             InlineKeyboardButton(text="ВТ", callback_data='tuesday1'),
                             InlineKeyboardButton(text='СР', callback_data='wednesday1'),
                             InlineKeyboardButton(text='ЧТ', callback_data='thrusday1'),
                             InlineKeyboardButton(text='ПТ', callback_data='friday1'),
                             InlineKeyboardButton(text='СБ', callback_data='saturday1')],
                            [InlineKeyboardButton(text='Сегодня', callback_data='today')]]
        schedule_markup = InlineKeyboardMarkup(inline_keyboard=builder_schedule)
        todayIs = _today() #Определение сегодняшнего дня недели
        await message.answer(f'На какой день нужно расписание?\nЧислитель (верх)\Знаменатель (низ)\n{todayIs}',
                             reply_markup=schedule_markup)
    elif message.text == 'Новости':
        builder_schedule = [[InlineKeyboardButton(text='Старостат 5', callback_data='starostat05'),
                             InlineKeyboardButton(text='Группа Вк 5', callback_data='group05'),
                             InlineKeyboardButton(text='Трудоустройство 5', callback_data='job05')],
                             [InlineKeyboardButton(text='Старостат 10', callback_data='starostat10'),
                             InlineKeyboardButton(text='Группа Вк 10', callback_data='group10'),
                             InlineKeyboardButton(text='Трудоустройство 10', callback_data='job10')]]
        schedule_markup = InlineKeyboardMarkup(inline_keyboard=builder_schedule)
        await message.answer(f'Какие новости вам нужны и сколько?\n',
                             reply_markup=schedule_markup)

        #await news(message.from_user.id, message)

        
    elif message.text == '1':
        await message.answer('Запрос на склеивание новостей принят!')
        await update_news_table(message)
    elif message.text == 'Уведомления':
        await state.set_state(Form.time_sleep_notifications)
        builder_time_lesson = [[InlineKeyboardButton(text='Отключить все уведомления', callback_data='off_notifications')]]
        time_lesson_markup = InlineKeyboardMarkup(inline_keyboard=builder_time_lesson)
        await message.answer('За сколько вы хотите получать уведомления о предстоящих парах?\nВведите время в минутах: ', reply_markup=time_lesson_markup)
    elif message.text == 'test':
        await time_sleep_notifications(message)
    elif message.text == 'Запуск погоды':
        await weather(message)
    elif message.text == '🛎 Запуск уведомлений':
        await time_sleep_notifications(message)
    elif message.text == 'Профиль':
        await lk(message)
    elif message.text == 'Запуск вк групп':
        await vk_groups(message)
    elif message.text == 'Запуск склейки':
        await update_news_table(message)
    #не работает проблемы с Sql запросом  ORA-01008
    elif message.text == 'Запуск оповещения об упоминании':
        await send_like_message(message)
    else:
        print('Бывает')

def main() -> None:
    dp.include_router(form_router)
    bot = Bot(TOKEN, parse_mode="html")
    # And the run events dispatching
    dp.run_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
