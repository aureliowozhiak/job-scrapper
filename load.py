from datetime import datetime
import sqlite3
import json
import os

# Diretório de saída
output_directory = "output"

# Data atual
current_year = datetime.now().year
current_month = datetime.now().month
current_day = datetime.now().day

# Caminho do diretório com os arquivos JSON
json_directory = f"{output_directory}/{current_year}/{current_month}/{current_day}"

if not os.path.exists(json_directory):
    print(f"Diretório '{json_directory}' não encontrado. Nenhum dado será processado.")
else:
    # Conexão com banco de dados local
    connection = sqlite3.connect("jobs.db")
    cursor = connection.cursor()

    # Criar tabela se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            company TEXT NOT NULL
        )
    """)

    # Lista de arquivos JSON no diretório
    try:
        json_files = os.listdir(json_directory)
    except FileNotFoundError:
        print(f"Diretório '{json_directory}' não encontrado.")
        json_files = []

    # Lista para armazenar os dados JSON
    json_data_list = []

    # Ler e armazenar os conteúdos dos arquivos JSON
    for json_filename in json_files:
        json_filepath = os.path.join(json_directory, json_filename)

        # Verifica se é um arquivo JSON
        if not json_filename.endswith(".json"):
            print(f"Ignorando '{json_filename}' (não é um arquivo JSON).")
            continue

        try:
            with open(json_filepath, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
                if isinstance(data, list):
                    json_data_list.append(data)
                else:
                    print(f"Aviso: Arquivo '{json_filename}' não contém uma lista válida.")
        except json.JSONDecodeError:
            print(f"Erro ao ler '{json_filename}': JSON inválido.")

    # Inserir dados no banco de dados
    for json_data in json_data_list:
        for data_entry in json_data:
            for position in data_entry:
                try:
                    title = position["title"]
                    link = str(position["link"])
                    company = position["company"]

                    if title and link and company:  # Verifica se os campos não estão vazios
                        cursor.execute(
                            "INSERT INTO positions (title, link, company) VALUES (?, ?, ?)",
                            (title, link, company),
                        )
                    else:
                        print(f"Aviso: Dados inválidos ignorados -> {position}")

                except KeyError as e:
                    print(f"Erro: Chave ausente {e} no JSON.")

    # Salvar e fechar conexão
    connection.commit()
    connection.close()
