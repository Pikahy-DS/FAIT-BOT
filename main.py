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

#InlineKeyboardMarkup form_router schedule

import interaction_inside

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
    await interaction_inside.cancel_handler(message,state)


# Этап регистрации при отсутсвии аккаунта в базе
#-
@form_router.message(Form.type_group_teacher, F.text == "Студент")
async def process_type_group(message: Message, state: FSMContext) -> None:
    """Этап регистрации при отсутсвии аккаунта в базе для студента

    Args:
         message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    await interaction_inside.process_type_group(message,state)
    

#-
@form_router.message(Form.type_group_teacher, F.text == "Преподаватель")
async def process_type_teacher(message: Message, state: FSMContext) -> None:
    """Этап регистрации при отсутсвии аккаунта в базе для преподователей

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """  
    await interaction_inside.process_type_teacher(message,state)


@form_router.message(Form.name)
async def process_name(message: Message, state: FSMContext) -> None:
    """Функция проверки принадлежит ли студент к существующим группам или преподователям и запуск нужной для регистарции

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    await interaction_inside.process_name(message,state)

@form_router.message(Form.time_sleep_notifications)
async def process_time_sleep_notifications(message: Message, state: FSMContext) -> None:
    """Запуск функций включени уведомления в виде стадий 

    Args:
        message (Message): сообщение из которого можно достать всю инфу о пользователе
        state (FSMContext): содержит ссылку на шаги и прошлую информацию о этих шагах
    """    
    await interaction_inside.process_time_sleep_notifications(message,state)

# # Обработка инлайн кнопок
@form_router.callback_query(lambda c: c.data)
async def call_handle(call: types.callback_query) -> None:
    """Обработка инлайн кнопок для пользователя (кнопки которые есть в сообщении пользователю)

    Args:
        call (types.callback_query): Ответ который присвоен каждой кнопке и при нажатии на которую вернётся 
        для дальнейшей обработки
    """ 
    await interaction_inside.call_handle(call)       

async def sleep_test():
    """сейчас не используется 
    """    
    flag = True
    count = 0
    while flag:
        print(f"Итерация - {count}")

        count = count + 1
        await asyncio.sleep(5)

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
    await interaction_inside.text_button(message,state)

def main() -> None:
    dp.include_router(form_router)
    bot = Bot(TOKEN, parse_mode="html")
    # And the run events dispatching
    dp.run_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
