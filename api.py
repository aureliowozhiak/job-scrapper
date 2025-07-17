import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

def search(word):
    connection = sqlite3.connect("jobs.db")
    cursor = connection.cursor()

    query = "SELECT link FROM positions WHERE UPPER(title) LIKE UPPER(?)"
    cursor.execute(query, (f"%{word}%",))  # Previne SQL Injection

    results = [row[0] for row in cursor.fetchall()]  # Obtém os resultados

    connection.close()

    return results


@app.route("/positions")
def positions():
    word = request.args.get("word", "")  # Obtém o parâmetro "word" da URL

    if not word:
        return jsonify({"error": "Parâmetro 'word' é obrigatório"}), 400

    search_results = search(word)

    return jsonify({"results": search_results})  # Retorna os links como JSON


@app.route("/", methods=["GET", "POST"])
def web():
    results = []
    error = None
    word = ""
   
    if request.method == "POST":
        word = request.form.get("word", "")
        if not word:
            error = "Parâmetro 'word' é obrigatório"
        else:
            results = search(word)
    return f"""
    <html>
        <head>
            <title>Busca de Vagas</title>
            <style>
                body {{
                    background: #f5f6fa;
                    font-family: Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                }}
                .container {{
                    background: #fff;
                    padding: 32px 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
                    text-align: center;
                }}
                h1 {{
                    color: #273c75;
                    margin-bottom: 24px;
                }}
                form {{
                    margin-bottom: 18px;
                }}
                input[type="text"] {{
                    padding: 10px;
                    border: 1px solid #dcdde1;
                    border-radius: 6px;
                    width: 220px;
                    font-size: 16px;
                }}
                button {{
                    padding: 10px 22px;
                    background: #4078c0;
                    color: #fff;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.2s;
                }}
                button:hover {{
                    background: #273c75;
                }}
                ul {{
                    list-style: none;
                    padding: 0;
                    margin-top: 18px;
                }}
                li {{
                    margin-bottom: 10px;
                }}
                a {{
                    color: #4078c0;
                    text-decoration: none;
                    font-weight: bold;
                    transition: color 0.2s;
                }}
                a:hover {{
                    color: #273c75;
                    text-decoration: underline;
                }}
                .error {{
                    color: #e84118;
                    margin-bottom: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Buscar Vagas</h1>
                <form method="post">
                    <input type="text" name="word" placeholder="Digite o termo da vaga" value="{word}">
                    <button type="submit">Buscar</button>
                </form>
                {"<div class='error'>" + error + "</div>" if error else ""}
                <ul>
                    {''.join(f"<li><a href='{link}' target='_blank'>{link}</a></li>" for link in results)}
                </ul>
            </div>
        </body>
    </html>
    """



if __name__ == "__main__":
    app.run(debug=True)
