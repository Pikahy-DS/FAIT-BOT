import urllib.request


for prep in range(1960, 4000):
    try:
        fp = urllib.request.urlopen(f"http://r.sf-misis.ru/group/{prep}")
        mybytes = fp.read()

        mystr = mybytes.decode("utf8")
        fp.close()

        start = mystr.find('<title>')
        start += 22

        end = mystr.find(' ::')

        fio = mystr[start:end]
        if fio:
            print(prep, mystr[start:end])

    except:
        None
