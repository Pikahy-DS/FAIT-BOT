import datetime
date1 = datetime.datetime.now().strftime('%H:%M')
print(date1[0:2])
lesson_time = {1: '09:00-10:30',
               2: '10:40-12:10',
               3: '12:40-14:10',
               4: '14:20-15:50',
               5: '16:00-17:30',
               6: '18:30-20:00',
               7: '20:10-21:40'}
number_l = 7
date_delta = (int(lesson_time[number_l][0:2])*60+int(lesson_time[number_l][3:5])) - (int(date1[0:2])*60 + int(date1[3:5]))
print(date_delta)
print([f'У вас скоро начнется {number_l} пара:' if abs(date_delta) < 10 else 'Через 10 минут нет пары'][0])

if abs(date_delta) < 10:
    print(f'У вас скоро начнется {number_l} пара:')