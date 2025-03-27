from bs4 import BeautifulSoup

class Transform:
    def __init__(self):
        pass

    def soupHtml(self, html_text):
        return BeautifulSoup(html_text, "html.parser")

    def getJobs(self, site_source, soup):
        match site_source:
            case "weworkremotely":
                return self.handleWeWorkRemotely(soup)
            case _:
                return "not found"

    def handleWeWorkRemotely(self, soup):
        jobs = []

        # Seleciona todas as vagas na página
        for job in soup.select('.new-listing-container'):
            title_tag = job.select_one('.new-listing__header__title')
            company_tag = job.select_one('.new-listing__company-name')
            location_tag = job.select_one('.new-listing__company-headquarters')
            salary_tag = job.select('.new-listing__categories__category')


            # Pegando os textos e removendo espaços extras
            title = title_tag.text.strip() if title_tag else 'N/A'
            company = company_tag.text.strip() if company_tag else 'N/A'
            location = location_tag.text.strip() if location_tag else 'N/A'
            
            # Pegando o salário se disponível
            salary = 'N/A'
            if salary_tag and len(salary_tag) > 1:
                salary = salary_tag[1].text.strip()

            links = [f"{'https://weworkremotely.com'}{a['href']}" for a in job.find_all('a', href=True)]

            # Criando dicionário com as informações
            jobs.append({
                'title': title,
                'company': company,
                'location': location,
                'salary': salary,
                'link': links
            })

        return jobs


        
