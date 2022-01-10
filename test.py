import logging
import asyncio
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

lesson_time = {1: '9:00-10:30',
               2: '10:40-12:10',
               3: '12:40-14:10',
               4: '14:20-15:50',
               5: '16:00-17:30',
               6: '18:30-20:00',
               7: '20:10-21:40'}

time_sleep_lesson = []

builder_main = [[KeyboardButton(text='Расписание'),
                 KeyboardButton(text='Новости'),
                 KeyboardButton(text = 'Уведомления')],
                [KeyboardButton(text='/delete')]]
markup_main = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_main)


async def insert_varible_into_table_group(id_user, group_name, message: Message):
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


async def insert_varible_into_table_teacher(id_user, FIO, message: Message):
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


async def read_lesson_teacher(id_user, daynum, weeknum, message: Message):
    group_name_users = """SELECT lower(FIO) from users where id_user =: id_user"""
    records = cursor.execute(group_name_users, [id_user]).fetchall()
    teachers = records[0][0]
    sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
    num = cursor.execute(sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
    print(records[0][0], daynum, weeknum)
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
            print(f'{row[1]} пара - {lesson_time[row[1]]}:\n{row[2]}\n{", ".join(d[key])}\n{row[3]}\n{row[5]}')
            d[key] = []

        # bot.send_message(message.chat.id, f"http://r.sf-misis.ru/teacher/{num[0][0]}")
    else:
        daynum_schedule = ['понедельник' if daynum == 1 else ('вторник' if daynum == 2 else (
            'среду' if daynum == 3 else ('четверг' if daynum == 4 else (
                'пятницу' if daynum == 5 else ('субботу' if daynum == 6 else ('воскресенье'))))))]
        week_schedule = ['числителю' if weeknum == 0 else ('знаменателю')]
        await message.answer(f'У вас в {daynum_schedule[0]} по {week_schedule[0]} нет пар!')


async def read_lesson(id_user, daynum, weeknum, message: Message):
    group_name_users = """SELECT group_name from users where id_user =: id_user"""
    records = cursor.execute(group_name_users, [id_user]).fetchall()
    group_name = records[0][0]
    sql = """SELECT * FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
    num = cursor.execute(sql, {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
    print(records[0][0], daynum, weeknum)
    if num:
        for row in num:
            print(row)
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


# Вывод расписания
async def schedule(id_user, daynum, weeknum, message: Message):
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

async def update_news_table(message: Message):
    flag = True
    news_count = 0
    while flag:
        news_rownum_sql = """SELECT id_news, date_news, time_news, author, text from starostat_news"""
        rownum_sql = cursor.execute(news_rownum_sql, ).fetchall()
        print(rownum_sql[0])
        count = 0
        for i in range(1, len(rownum_sql)):
            if rownum_sql[i][1] == rownum_sql[i - 1][1] and rownum_sql[i][2][0:5] == rownum_sql[i - 1][2][0:5] and \
                    rownum_sql[i - 1][3] == rownum_sql[i][3]:
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
                print('успешно: ', rownum_sql[i - 1][4] + '\n' + rownum_sql[i][4], ' ', [rownum_sql[i][0]])
                news_count = news_count + 1
                break
            else:
                count = count + 1
                # print(rownum_sql[i-1][2][0:5],int(rownum_sql[i-1][2][3:5])-1)
                if count == len((rownum_sql)) - 1:
                    flag = False
    if news_count > 0:
        await message.answer(f'Успешно склеено {news_count} новости(ей)')
    else:
        await message.answer("Отсутствуют новости для склеивания")


async def news(id_user, message: Message):
    news_rownum_sql = """SELECT id_news from starostat_news"""
    rownum_sql = cursor.execute(news_rownum_sql, ).fetchall()
    end_news = int(len(rownum_sql))

    news_news_sql = """SELECT date_news, time_news, author, text, id_news from starostat_news"""
    records = cursor.execute(news_news_sql, ).fetchall()

    news_rownum_user_news_view = """SELECT news_view from users where id_user =: id_user"""
    news_rownum = cursor.execute(news_rownum_user_news_view, [id_user]).fetchall()
    count = 0
    print(records[0], records[0][1], records[1][1])
    for row in news_rownum:
        news_rownum_news = str(row[0])
    for i in records:
        news_rownum_count = news_rownum_news.split(',')
        test_1 = str(i[4]).split(' ')
        print(str(test_1[0]) not in news_rownum_count)

        if str(test_1[0]) not in news_rownum_count:
            news_rownum_news = news_rownum_news + ',' + str(i[4])
            update_rownum = """UPDATE users SET news_view =: news_rownum_news where id_user =: id_user"""
            update_rownum_news = cursor.execute(update_rownum,
                                                {'news_rownum_news': news_rownum_news, 'id_user': id_user})
            conn.commit()
            await message.answer(f'{i[2]}\n {i[0]} - {i[1]}\n{i[3]}')
            count = count + 1
    if count == 0:
        await message.answer(f'Вы все просмотрели, новых сообщений нет!')


async def news_all(id_user):
    news_rownum_user = """SELECT news_view from users"""
    news_rownum = cursor.execute(news_rownum_user, ).fetchall()
    mews = news_rownum[0][0]
    news_news_user = """SELECT date_news, time_news, author, text from starostat_news where id_news <>: mews"""
    news_news = cursor.execute(news_news_user, [mews]).fetchall()
    print(news_news)

    # builder_i = [
    #     [InlineKeyboardButton(text='ПН', callback_data='ss'), InlineKeyboardButton(text='ВТ', callback_data='sdsa'),
    #      InlineKeyboardButton(text='СР', callback_data='sdsa'), InlineKeyboardButton(text='ЧТ', callback_data='sdsa'),
    #      InlineKeyboardButton(text='ПТ', callback_data='sdsa'), InlineKeyboardButton(text='СБ', callback_data='sdsa')]]
    # keyboard1 = InlineKeyboardMarkup(inline_keyboard=builder_i)
    # await message.answer("Как подавать котлеты?", reply_markup=keyboard1)

async def time_sleep_notifications(time_sleep, message: Message, state: FSMContext):
    # Сделать запросы раз в сутки, путем добавления все в переменные, для оптимизации
    text_lesson = None
    time_sleep_lesson.append(time_sleep)
    await message.answer(f'Уведомления за {time_sleep} минут успешно подключены')
    await state.clear()
    count = 0
    # Делаем пока пользователь хочет получать уведомления
    while time_sleep_lesson :
        for time_sleep_one in time_sleep_lesson:
            print(time_sleep_lesson)

            #Узнаем текущее время, дату и неделю
            date1 = datetime.datetime.now().strftime('%H:%M')
            weeknum = datetime.datetime.now().isocalendar().week % 2
            daynum = datetime.datetime.now().isocalendar().weekday

            #Проверяем есть ли в БД группа пользователя
            group_name_users = """SELECT group_name from users where id_user =: id_user"""
            records = cursor.execute(group_name_users, [message.from_user.id]).fetchall()
            group_name = records[0][0]
            print(group_name)

            #Если пользователь студент
            if group_name != 'None':
                sql = """SELECT number_lesson FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                num = cursor.execute(sql, {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                for i in num:
                    print(i[0])
                    number_l = i[0]
                    date_delta = (int(lesson_time[number_l][0:2]) * 60 + int(lesson_time[number_l][3:5])) - (int(date1[0:2]) * 60 + int(date1[3:5]))
                    text_lesson = [f'У вас через {time_sleep_one} минут начнется:' if abs(date_delta) == int(time_sleep_one) else 'None'][0]

                    #Если пора присылать уведомление
                    if text_lesson != 'None':
                        lesson_sql = """SELECT * from schedule where lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson"""
                        lesson = cursor.execute(lesson_sql, {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum, 'number_lesson': number_l}).fetchall()
                        for row in lesson:
                            print(row)
                            await message.answer(
                                f'{text_lesson}\n'
                                f'<u><b>{row[1]} пара - {lesson_time[row[1]]}</b></u>:\n'
                                f'<b>Предмет:</b> {row[2]}\n<b>Препод.:</b> {row[4]}\n'
                                f'<b>Формат: </b>{row[3]}\n<b>Аудитория:</b> {row[5]}')

            #Если пользователя преподаватель
            else:
                group_name_users = """SELECT lower(FIO) from users where id_user =: id_user"""
                records = cursor.execute(group_name_users, [message.from_user.id]).fetchall()
                teachers = records[0][0]
                sql = """SELECT number_lesson FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                num = cursor.execute(sql, {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                d = {}
                for i in num:
                    print(i[0])
                    number_l = i[0]
                    date_delta = (int(lesson_time[number_l][0:2]) * 60 + int(lesson_time[number_l][3:5])) - (int(date1[0:2]) * 60 + int(date1[3:5]))
                    text_lesson = [f'У вас через {time_sleep_one} минут начнется пара:' if abs(date_delta) == int(time_sleep_one) else 'None'][0]

                    #Если пора присылать уведомление
                    if text_lesson != 'None':
                        lesson_sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson ORDER BY number_lesson"""
                        lesson = cursor.execute(lesson_sql,{'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum, 'number_lesson': number_l}).fetchall()
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
                                await message.answer(
                                    f'<u><b>{row[1]} пара - {lesson_time[row[1]]}:</b></u>\n'
                                    f'<b>Предмет:</b> {row[2]}\n<b>Группа(ы):</b> {", ".join(d[key])}\n'
                                    f'<b>Формат:</b> {row[3]}\n<b>Аудитория:</b> {row[5]}')
                                print(
                                    f'{row[1]} пара - {lesson_time[row[1]]}:\n{row[2]}\n{", ".join(d[key])}\n{row[3]}\n{row[5]}')
                                d[key] = []

        #Проверка работоспособности
        print(f"Итерация - {count} ---- {text_lesson} --- {time_sleep}")
        count = count + 1
        await asyncio.sleep(60)

@form_router.message(commands={"cancel"})
@form_router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
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
@form_router.message(Form.type_group_teacher, F.text == "Студент")
async def process_type_group(message: Message, state: FSMContext) -> None:
    await state.update_data(type_group_teacher=message.text)
    print(message.text)
    await state.set_state(Form.name)
    await message.answer(f"Введите номер группы в формате - 'АТ-18-1д'", reply_markup=ReplyKeyboardRemove())


@form_router.message(Form.type_group_teacher, F.text == "Преподаватель")
async def process_type_teacher(message: Message, state: FSMContext) -> None:
    User = await state.update_data(type_group_teacher=message.text)
    await state.set_state(Form.name)
    builder_teacher = [
        [KeyboardButton(text='Цыганков Юрий Александрович'), KeyboardButton(text='Соловьев Антон Юрьевич')]]
    markup_teacher = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=builder_teacher)
    await message.answer('Введите ваше ФИО в полном формате.', reply_markup=markup_teacher)


@form_router.message(Form.name)
async def process_name(message: Message, state: FSMContext) -> None:
    User = await state.update_data(name=message.text)
    id_user = message.from_user.id
    if User['type_group_teacher'] == 'Студент':
        student_check_sql = """SELECT group_name from groups where lower(group_name) = lower(:group_name)"""
        student_check = cursor.execute(student_check_sql, [message.text]).fetchall()
        print(student_check)
        if student_check:
            await insert_varible_into_table_group(id_user, User['name'], message)
            print(User['name'])
            await state.clear()
        else:
            await message.answer('Вы ввели несуществующую группу, давайте начнем сначала')
            await command_start_handler(message, state)
    else:
        student_check_sql = """SELECT FIO from teachers where lower(FIO) = lower(:FIO)"""
        student_check = cursor.execute(student_check_sql, [message.text]).fetchall()
        print(student_check)
        if student_check:
            await insert_varible_into_table_teacher(id_user, User['name'], message)
            print(User['name'])
            await state.clear()
        else:
            await command_start_handler(message, state)
            await message.answer('Вы ввели несуществующего преподавателя, давайте начнем сначала')

@form_router.message(Form.time_sleep_notifications)
async def process_time_sleep_notifications(message: Message, state: FSMContext) -> None:
    time_state = await state.update_data(time_sleep_notifications=message.text)
    await time_sleep_notifications(time_state['time_sleep_notifications'], message, state)
    await state.clear()

# Обработка инлайн кнопок
@form_router.callback_query(lambda c: c.data)
async def call_handle(call: types.callback_query) -> None:
    if call.data == 'monday0':
        print('one')
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
        time_sleep_lesson.clear()
        print(time_sleep_lesson)
        #Добавить столбец с временами уведомлений и очищать его при нажатии на кнопку, в виде запроса запрашивать время уведомлений.
    else:
        print(call)


async def sleep_test():
    flag = True
    count = 0
    while flag:
        print(f"Итерация - {count}")

        count = count + 1
        await asyncio.sleep(1)



# Действия при вводе /start
@form_router.message(commands={"start"})
async def command_start_handler(message: Message, state: FSMContext) -> None:
    id_user = message.from_user.id
    print(message.from_user.id)
    group_name_users = """SELECT group_name from users where id_user =: id_user"""
    records = cursor.execute(group_name_users, [message.from_user.id]).fetchall()
    print(records)
    if records:
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
        await message.answer(f'На какой день нужно расписание?\nЧислитель (верх)\Знаменатель (низ)',
                             reply_markup=schedule_markup)
    elif message.text == 'Новости':
        await news(message.from_user.id, message)
    elif message.text == '1':
        await message.answer('Запрос на склеивание новостей принят!')
        await update_news_table(message)
    elif message.text == 'Уведомления':
        await state.set_state(Form.time_sleep_notifications)
        builder_time_lesson = [[InlineKeyboardButton(text='Отключить все уведомления', callback_data='off_notifications')]]
        time_lesson_markup = InlineKeyboardMarkup(inline_keyboard=builder_time_lesson)
        await message.answer('За сколько вы хотите получать уведомления о предстоящих парах?\nВведите время в минутах: ', reply_markup=time_lesson_markup)
    elif message.text == 'test':
        await sleep_test()
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
