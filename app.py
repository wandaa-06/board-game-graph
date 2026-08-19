import os
import math

from flask import Flask, render_template, request, abort
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

import queries

load_dotenv()

URI = os.getenv("COGNODB_URI")
USER = os.getenv("COGNODB_USER")
PASSWORD = os.getenv("COGNODB_PASSWORD")

app = Flask(__name__)

_driver = None


def get_driver():
    """Lazily create a single shared CognoDB driver."""
    global _driver

    if _driver is None:
        _driver = GraphDatabase.driver(
            URI,
            auth=(USER, PASSWORD)
        )

    return _driver


@app.errorhandler(ServiceUnavailable)
@app.errorhandler(AuthError)
def handle_db_down(error):
    return render_template(
        "db_error.html",
        error=str(error)
    ), 503


@app.route("/")
def home():
    driver = get_driver()

    mechanic = request.args.get("mechanic") or None
    theme = request.args.get("theme") or None

    # Get games using the existing working query.
    games = queries.list_games(
        driver,
        mechanic=mechanic,
        theme=theme
    )

    # Build the dropdown values from the same game data.
    # This avoids relying on separate list_mechanics/list_themes queries.
    all_mechanics = sorted({
        mechanic_name
        for game in games
        for mechanic_name in game.get("mechanics", [])
        if mechanic_name
    })

    all_themes = sorted({
        theme_name
        for game in games
        for theme_name in game.get("themes", [])
        if theme_name
    })

    return render_template(
        "index.html",
        games=games,
        all_mechanics=all_mechanics,
        all_themes=all_themes,
        selected_mechanic=mechanic,
        selected_theme=theme
    )


@app.route("/game/<game_name>")
def game_detail(game_name):
    driver = get_driver()

    game = queries.get_game(
        driver,
        game_name
    )

    if game is None:
        abort(404)

    recommendations = queries.recommend_by_shared_mechanics(
        driver,
        game_name,
        min_shared=1
    )

    # Create positions for the connection web
    web_nodes = []

    visible_recommendations = recommendations[:8]
    count = len(visible_recommendations)

    for i, rec in enumerate(visible_recommendations):
        angle = (
            2 * math.pi * i / count
            if count
            else 0
        )

        web_nodes.append({
            "name": rec["recommended_game"],
            "shared_mechanics": rec["shared_mechanics"],
            "shared_count": rec["shared_count"],
            "x": 50 + 35 * math.cos(angle),
            "y": 50 + 35 * math.sin(angle)
        })

    return render_template(
        "game.html",
        game=game,
        recommendations=recommendations,
        web_nodes=web_nodes
    )


@app.route("/path")
def path_finder():
    driver = get_driver()

    game_a = request.args.get("game_a") or None
    game_b = request.args.get("game_b") or None

    games = queries.list_games(driver)

    game_names = [
        game["name"]
        for game in games
    ]

    result = None
    searched = bool(game_a and game_b)

    if searched:
        if game_a == game_b:
            result = {
                "path_nodes": [game_a],
                "hops": 0
            }
        else:
            result = queries.shortest_connection(
                driver,
                game_a,
                game_b
            )

    return render_template(
        "path.html",
        games=game_names,
        game_a=game_a,
        game_b=game_b,
        result=result,
        searched=searched
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
