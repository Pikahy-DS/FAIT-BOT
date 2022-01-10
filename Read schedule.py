import urllib.request
import requests
import sqlite3
from bs4 import BeautifulSoup
data = []


def insert_varible_into_table(group_name, number_lesson, lesson, format, teacher, audience, day_number):
    try:
        sqlite_connection = sqlite3.connect('data.db')
        cursor = sqlite_connection.cursor()
        print("Подключен к SQLite")
        print(group_name, number_lesson, lesson, format, teacher, audience, day_number)
        sqlite_insert_with_param = """INSERT INTO schedule
                              (group_name, number_lesson, lesson,format, teacher, audience, day_number)
                              VALUES (?, ?,?, ?, ?, ?, ?);"""

        data_tuple = (group_name, number_lesson, lesson,format, teacher, audience, day_number)
        cursor.execute(sqlite_insert_with_param, data_tuple)
        sqlite_connection.commit()
        print("Переменные Python успешно вставлены в таблицу teacher")
        cursor.close()
    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")
# # with open("Teachers.txt", 'r', encoding='utf-8') as f:
# #     for line in f:
# #         data.append([str(x) for x in line.split(' ')])
# for i in range(len(data)):
#     name = data[i][1] + ' ' + data[i][2] + ' '+ data[i][3]
#     print(data[i][0],name)
#     insert_varible_into_table(name,data[i][0])


def read_sqlite_table():
    try:
        sqlite_connection = sqlite3.connect('data.db')
        cursor = sqlite_connection.cursor()
        print("Подключен к SQLite")

        sqlite_select_query = """SELECT * from groups"""
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()
        print("Всего строк:  ", len(records))

        for row in records:
            today = 0  #дни недели
            while today <= 6:
                lesson = 0 #пара по счету
                while lesson < 7:
                    print(row[0],' ',lesson, ' ', today)
                    url = 'http://r.sf-misis.ru/group/'
                    page = requests.get(url + str(row[1]))
                    soup = BeautifulSoup(page.text, 'lxml')
                    one = soup.find_all('tr')[today + 1]('td')[lesson]

                    lesson_name_table = one.find_all("div",{'class': 'table-subject'})
                    lesson_name = str([item.get_text().strip() for item in lesson_name_table])[2:-2]
                    if lesson_name != '':
                        href_teacher_table = one.find_all("div", {'class': 'table-teacher'})
                        for item in href_teacher_table:
                            hh = item.find("a").get('href').split('/')
                            href_teacher = str(hh[2])

                        # Запрашиваем href из таблицы teachers, так как в расписании ФИО сокращенное
                        teacher_sql = cursor.execute("""SELECT FIO FROM teachers WHERE href = ?""", (href_teacher,))
                        teacher_FIO = str([t for t in teacher_sql])[3:-4]

                        format_table = one.find_all("div", {'class': 'table-lessontype'})
                        format = str([item.get_text().strip() for item in format_table])[2:-2]

                        audience_table = one.find_all("div", {'class': 'table-room'})
                        audience = str([item.get_text().strip() for item in audience_table])[2:-2]
                        print(row[0], lesson + 1, lesson_name, format, teacher_FIO, audience, today + 1, 0)
                        sqlite_insert_with_param = """INSERT INTO schedule
                                              (group_name, number_lesson, lesson,format, teacher, audience, day_number, week)
                                              VALUES (?, ?,?, ?, ?, ?, ?, ?);"""
                        # данные, которые записываем в таблицу, последнее значение означает неделю: 0 - числитель, 1 - знаменатель
                        data_tuple = (row[0], lesson + 1, lesson_name, format, teacher_FIO, audience, today + 1, 1)
                        cursor.execute(sqlite_insert_with_param, data_tuple)
                        print("Переменные Python успешно вставлены в таблицу teacher")
                        sqlite_connection.commit()
                        # insert_varible_into_table(str('АТ-18-1д'), lesson + 1, lesson_name, format, teacher_FIO, audience, today + 1)

                    else:
                        pass
                    lesson = lesson + 1
                today = today + 1

    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")

read_sqlite_table()