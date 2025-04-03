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

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/positions")
def positions():
    word = request.args.get("word", "")  # Obtém o parâmetro "word" da URL

    if not word:
        return jsonify({"error": "Parâmetro 'word' é obrigatório"}), 400

    search_results = search(word)

    return jsonify({"results": search_results})  # Retorna os links como JSON

if __name__ == "__main__":
    app.run(debug=True)
