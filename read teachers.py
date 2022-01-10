import urllib.request

for prep in range(1000):
    try:
        fp = urllib.request.urlopen(f"http://r.sf-misis.ru/teacher/{prep}")
        mybytes = fp.read()

        mystr = mybytes.decode("utf8")
        fp.close()

        start = mystr.find('<title>')
        start += 7

        end = mystr.find(' ::')

        fio = mystr[start:end]
        if fio:
            print(prep, mystr[start:end])

    except:
        None
