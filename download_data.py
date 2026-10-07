import os
import urllib.request

os.makedirs("data", exist_ok=True)
URL = "https://raw.githubusercontent.com/justmarkham/pycon-2016-tutorial/master/data/sms.tsv"
urllib.request.urlretrieve(URL, "data/sms.tsv")
print("Downloaded data/sms.tsv")