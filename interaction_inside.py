# Обработка инлайн кнопок


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





import main
import interaction_database
import interaction_user



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

async def process_type_group(message: Message, state: FSMContext) -> None:
    """Этап регистрации при отсутсвии аккаунта в базе для студента

    Args:
         message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    
    await state.update_data(type_group_teacher=message.text)
    #print(message.text)
    await state.set_state(main.Form.name)
    await message.answer(f"Введите номер группы в формате - 'АТ-18-1д'", reply_markup=ReplyKeyboardRemove())

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
        weeknum = datetime.datetime.now().isocalendar()[1]%2 
        daynum = datetime.datetime.now().isocalendar()[2]  
        await call.answer(f'Вы выбрали пары на сегодня')
        await call.message.edit_text(f'Пары сегодня: ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        await schedule(call.from_user.id, daynum, weeknum, call.message)
    elif call.data == 'off_notifications':
        await interaction_user.delete_time_sleep_notifications(call.message)
        await call.answer(f'Все уведомления отключены')
        await call.message.edit_text(f'Все уведомления отключены ',
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        #Добавить столбец с временами уведомлений и очищать его при нажатии на кнопку, в виде запроса запрашивать время уведомлений.
    elif call.data[:-2] == "starostat":
        await call.message.edit_text(f'Новости из старостата')
        await interaction_database.news(call.from_user.id, call.message,call.data)
    elif call.data[:-2] == "group":
        await call.message.edit_text(f'Новости из группы')
        await interaction_database.news(call.from_user.id, call.message,call.data)
    elif call.data[:-2] == "job":
        await call.message.edit_text(f'Новости по трудоустройству')
        await interaction_database.news(call.from_user.id, call.message,call.data)
    
    else:
        print(call)


async def process_type_teacher(message: Message, state: FSMContext) -> None:
    """Этап регистрации при отсутсвии аккаунта в базе для преподователей

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """  
    
    User = await state.update_data(type_group_teacher=message.text)
    await state.set_state(main.Form.name)
    builder_teacher = [
        [KeyboardButton(text='Цыганков Юрий Александрович'), KeyboardButton(text='Соловьев Антон Юрьевич')]]
    markup_teacher = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_teacher)
    await message.answer('Введите ваше ФИО в полном формате.', reply_markup=markup_teacher)

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
        records = main.cursor.execute(group_name_users, [id_user]).fetchall()
        if records[0][0] != None:
            await interaction_database.read_lesson(id_user, daynum, weeknum, message)
        else:
            await interaction_database.read_lesson_teacher(id_user, daynum, weeknum, message)
    except:
        await message.answer('Ошибка, введите команду /start')

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
        student_check = main.cursor.execute(student_check_sql, [message.text]).fetchall()
        #print(student_check)
        if student_check:
            await interaction_database.insert_varible_into_table_group(id_user, User['name'], message)
            #print(User['name'])
            await state.clear()
        else:
            await message.answer('Вы ввели несуществующую группу, давайте начнем сначала')
            await main.command_start_handler(message, state)
    else:
        student_check_sql = """SELECT FIO from teachers where lower(FIO) = lower(:FIO)"""
        student_check = main.cursor.execute(student_check_sql, [message.text]).fetchall()
        #print(student_check)
        if student_check:
            await interaction_database.insert_varible_into_table_teacher(id_user, User['name'], message)
            #print(User['name'])
            await state.clear()
        else:
            await main.command_start_handler(message, state)
            await message.answer('Вы ввели несуществующего преподавателя, давайте начнем сначала')


async def process_time_sleep_notifications(message: Message, state: FSMContext) -> None:
    """Запуск функций включени уведомления в виде стадий 

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    
    time_state = await state.update_data(time_sleep_notifications=message.text)
    await interaction_user.time_sleep_notifications_add(time_state['time_sleep_notifications'], message, state)
    await state.clear()

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
        #interaction_inside
        
    elif message.text == '1':
        await message.answer('Запрос на склеивание новостей принят!')
        await update_news_table(message)
    elif message.text == 'Уведомления':
        
        await state.set_state(main.Form.time_sleep_notifications)
        builder_time_lesson = [[InlineKeyboardButton(text='Отключить все уведомления', callback_data='off_notifications')]]
        time_lesson_markup = InlineKeyboardMarkup(inline_keyboard=builder_time_lesson)
        await message.answer('За сколько вы хотите получать уведомления о предстоящих парах?\nВведите время в минутах: ', reply_markup=time_lesson_markup)
    elif message.text == 'test':
        await interaction_user.time_sleep_notifications(message)
    elif message.text == 'Запуск погоды':
        await interaction_user.weather(message)
    elif message.text == '🛎 Запуск уведомлений':
        await interaction_user.time_sleep_notifications(message)
    elif message.text == 'Профиль':
        await interaction_database.lk(message)
    elif message.text == 'Запуск вк групп':
        await interaction_database.vk_groups(message)
    elif message.text == 'Запуск склейки':
        await update_news_table(message)
    #не работает проблемы с Sql запросом  ORA-01008
    elif message.text == 'Запуск оповещения об упоминании':
        await interaction_user.send_like_message(message)
    else:
        print('Бывает')

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
        records = main.cursor.execute(group_name_users, [id_user]).fetchall()
        if records[0][0] != None:
            await interaction_database.read_lesson(id_user, daynum, weeknum, message)
        else:
            await interaction_database.read_lesson_teacher(id_user, daynum, weeknum, message)
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
            rownum_sql = main.cursor.execute(news_rownum_sql, ).fetchall()
            #print(rownum_sql[0])
            count = 0
            for i in range(1, len(rownum_sql)):
                if rownum_sql[i][1] == rownum_sql[i - 1][1] and rownum_sql[i][2][0:5] == rownum_sql[i - 1][2][0:5] and rownum_sql[i - 1][3] == rownum_sql[i][3] and (len(rownum_sql[i][4].encode('utf-8'))+len(rownum_sql[i-1][4].encode('utf-8'))) < 4000:
                    #print(len(rownum_sql[i-1][4].encode('utf-8')), ' -------------------------', len(rownum_sql[i][4].encode('utf-8')))
                    update_table_str = """UPDATE starostat_news SET text =: text  where id_news =: id_news"""
                    text = rownum_sql[i - 1][4] + '\n' + rownum_sql[i][4]
                    id_news = rownum_sql[i - 1][0]
                    update_table_dict = {'text': text, 'id_news': id_news}
                    update_table = main.cursor.execute(update_table_str, update_table_dict)
                    main.conn.commit()
                    id_news_d = rownum_sql[i][0]
                    delete_table_str = """DELETE FROM starostat_news where id_news =: id_news_d"""
                    delete_table = main.cursor.execute(delete_table_str, [id_news_d])
                    main.conn.commit()
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