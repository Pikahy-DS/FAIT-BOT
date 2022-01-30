import cx_Oracle
conn = cx_Oracle.connect('hr/hr2020@ORCLPDB')
cursor = conn.cursor()
count = 0
flag_time_sleep = True
# Делаем пока пользователь хочет получать уведомления
while flag_time_sleep == True:
    select_time_sleep_sql = """SELECT id_user,group_name,FIO,notifications from users"""
    select_time_sleep = cursor.execute(select_time_sleep_sql, ).fetchall()
    print(select_time_sleep)
    for j in range(0,len(select_time_sleep)):
        str_select_time_sleep = select_time_sleep[j][3]
        print(str_select_time_sleep)
        for time_sleep_one in str_select_time_sleep.split(','):
            print(time_sleep_one)
            # Узнаем текущее время, дату и неделю
            date1 = datetime.datetime.now().strftime('%H:%M')
            weeknum = datetime.datetime.now().isocalendar().week % 2
            daynum = datetime.datetime.now().isocalendar().weekday

            text_lesson = None

            group_name = select_time_sleep[j][1]
            # Если пользователь студент
            if group_name is not None:
                print(group_name)
                sql = """SELECT number_lesson FROM schedule WHERE lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                num = cursor.execute(sql, {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                for i in num:
                    # print(i[0])
                    number_l = i[0]
                    date_delta = (int(lesson_time[number_l][0:2]) * 60 + int(lesson_time[number_l][3:5])) - (
                            int(date1[0:2]) * 60 + int(date1[3:5]))
                    text_lesson = [f'У вас через {time_sleep_one} минут начнется:' if date_delta == int(time_sleep_one) else 'None'][0]

                    # Если пора присылать уведомление
                    if text_lesson != 'None':
                        lesson_sql = """SELECT * from schedule where lower(group_name) = lower(:group_name) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson"""
                        lesson = cursor.execute(lesson_sql,
                                                {'group_name': group_name, 'daynum': daynum, 'weeknum': weeknum,
                                                 'number_lesson': number_l}).fetchall()
                        for row in lesson:
                            # print(row)
                            await message(select_time_sleep[j][0],
                                f'{text_lesson}\n'
                                f'<u><b>{row[1]} пара - {lesson_time[row[1]]}</b></u>:\n'
                                f'<b>Предмет:</b> {row[2]}\n<b>Препод.:</b> {row[4]}\n'
                                f'<b>Формат: </b>{row[3]}\n<b>Аудитория:</b> {row[5]}')
                        text_lesson = None

            # Если пользователя преподаватель
            else:
                teachers = select_time_sleep[j][2]
                print(teachers)
                sql = """SELECT DISTINCT (number_lesson) FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum ORDER BY number_lesson"""
                num = cursor.execute(sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum}).fetchall()
                print(num)
                d = {}
                for i in num:
                    # print(i[0])
                    number_l = i[0]
                    date_delta = (int(lesson_time[number_l][0:2]) * 60 + int(lesson_time[number_l][3:5])) - (
                            int(date1[0:2]) * 60 + int(date1[3:5]))
                    text_lesson = [f'У вас через {time_sleep_one} минут начнется:' if date_delta == int(time_sleep_one) else 'None'][0]

                    # Если пора присылать уведомление
                    if text_lesson != 'None':
                        lesson_sql = """SELECT * FROM schedule WHERE lower(teacher) = lower(:teachers) AND day_number = :daynum and week = :weeknum and number_lesson = :number_lesson ORDER BY number_lesson"""
                        lesson = cursor.execute(lesson_sql, {'teachers': teachers, 'daynum': daynum, 'weeknum': weeknum,
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
                                await message(select_time_sleep[j][0],
                                    f'{text_lesson}\n'
                                    f'<u><b>{row[1]} пара - {lesson_time[row[1]]}:</b></u>\n'
                                    f'<b>Предмет:</b> {row[2]}\n<b>Группа(ы):</b> {", ".join(d[key])}\n'
                                    f'<b>Формат:</b> {row[3]}\n<b>Аудитория:</b> {row[5]}')
                                # print(
                                #    f'{row[1]} пара - {lesson_time[row[1]]}:\n{row[2]}\n{", ".join(d[key])}\n{row[3]}\n{row[5]}')
                                d[key] = []
                text_lesson = None

            # Проверка работоспособности
            print(f"Итерация - {count} ---- {text_lesson} --- {time_sleep}")
    count = count + 1
    await asyncio.sleep(60)