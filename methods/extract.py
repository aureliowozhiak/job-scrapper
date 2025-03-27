import requests

class Extract:
    def __init__(self, urls, date, utils, path = "lake"):
        self.urls   = urls
        self.path   = path
        self.year   = date["year"]
        self.month  = date["month"]
        self.day    = date["day"]
        self.utils  = utils

    def extractData(self, query = "data engineer"):
        for site, data in self.urls.items():
            endpoint = data['url_q'] + query.replace(" ", "+")
            print(endpoint)
            if data["active"] == 1:
                self.utils.createDir(f"{self.path}/{self.year}/{self.month}/{self.day}/{site}")

            html_response = requests.get(endpoint)
            if html_response.status_code == 200 and data["active"] == 1:
                file_name_path = f"{self.path}/{self.year}/{self.month}/{self.day}/{site}/{query.replace(" ", "_")}.html"
                with open(file_name_path, "w") as f:
                    f.write(html_response.text)