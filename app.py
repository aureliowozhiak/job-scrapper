from endpoints import urls
from datetime import datetime
from methods.utils import Utils
from methods.extract import Extract
from methods.transform import Transform

# Configuração do ambiente / Criação de pastas

path    = "lake"
year    = datetime.now().year
month   = datetime.now().month
day     = datetime.now().day

utils = Utils()

utils.createDir(f"{path}")
utils.createDir(f"{path}/{year}")
utils.createDir(f"{path}/{year}/{month}")
utils.createDir(f"{path}/{year}/{month}/{day}")

extract = Extract(
    urls = urls,
    date = {
        "year"  : year,
        "month" : month,
        "day"   : day
    },
    utils = utils
)

queries = [
    "data analytics",
    "data engineer",
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "business intelligence analyst",
    "ETL developer",
    "big data engineer",
    "database administrator",
    "SQL developer",
    "Python developer data",
    "AI engineer",
    "cloud data engineer",
    "data architect",
    "BI developer",
    "data warehouse specialist",
    "analytics engineer",
    "data governance specialist",
    "quantitative analyst",
    "data product manager"
]

#for query in queries:
#    extract.extractData(query=query)

transform = Transform()

directories = utils.listDir(f"{path}/{year}/{month}/{day}")

for directory in directories:
    files = utils.listDir(f"{path}/{year}/{month}/{day}/{directory}")
    for file_name in files:
        html_text = utils.loadFile(f"{path}/{year}/{month}/{day}/{directory}/{file_name}")
        soup = transform.soupHtml(html_text)
        print(transform.getJobs(directory, soup))
        break
    break



