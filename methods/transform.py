from bs4 import BeautifulSoup

class Transform:
    def __init__(self):
        pass

    def soupHtml(self, html_text):
        return BeautifulSoup(html_text, "html.parser")

    def getJobs(self, site_source, soup):
        match site_source:
            case "remotar":
                return self.handleRemotar(soup)
            case _:
                return "not found"

    def handleRemotar(self, soup):
        vagas = soup.find_all("div", class_="css-v05qs0")

        lista_vagas = []

        for vaga in vagas:
            try:
                titulo = vaga.find("p", class_="h1").text.strip()
                link_vaga = vaga.find("a", href=True)["href"]
                empresa = vaga.find("p", class_="company").text.strip()
                empresa_link = vaga.find("a", href=True, rel="noopener noreferrer")["href"]
                publicacao = vaga.find("p", class_="created-at").text.strip()
                tipo_trabalho = vaga.find("div", class_="css-8xyatz").text.strip()
                salario = vaga.find("div", class_="info-salary-box").text.strip()
                imagem_empresa = vaga.find("img")["src"]

                lista_vagas.append({
                    "Título": titulo,
                    "Link da Vaga": f"https://remotar.com{link_vaga}",
                    "Empresa": empresa,
                    "Link da Empresa": f"https://remotar.com{empresa_link}",
                    "Publicado em": publicacao,
                    "Tipo de Trabalho": tipo_trabalho,
                    "Salário": salario,
                    "Imagem da Empresa": imagem_empresa
                })

                return lista_vagas
            except AttributeError:
                continue  # Se faltar algum campo, ignora e segue para a próxima

            
            
        