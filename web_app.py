from flask import Flask, render_template, jsonify, request
import random
import json
import os


# Загружаем данные о картах
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


cards_data = load_json("data/cards.json")  # Данные о картах

app = Flask(__name__)
# Главная страница с случайным раскладом
@app.route('/')
def index():
    # Рандомный выбор 4 карт
    selected_cards = random.sample(list(cards_data.items()), 4)

    return render_template("index.html", cards=selected_cards)


# Обработчик для получения данных о карте
@app.route('/get_card_description', methods=['POST'])
def get_card_description():
    card_id = request.json.get("card_id")
    card = cards_data.get(card_id)
    if card:
        return jsonify({
            "name": card["name"],
            "description": card["description"],
            "image": card["image"]
        })
    return jsonify({"error": "Card not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)