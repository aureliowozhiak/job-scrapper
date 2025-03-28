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

    def handleSkipTheDrive(self, soup):
        job_posts = []
    
        for article in soup.select("article.post"):
            title_element = article.select_one("h2.post-title a")
            company_element = article.select_one(".custom_fields_company_name_display_search_results")
            date_element = article.select_one("time.post-date")
            
            if title_element and company_element and date_element:
                job_posts.append({
                    "title": title_element.text.strip(),
                    "link": title_element["href"],
                    "company": company_element.text.strip(),
                    "date_posted": date_element["datetime"]
                })
        
        return job_posts
