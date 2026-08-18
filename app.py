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
    """Lazily create a single shared driver instance."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    return _driver


@app.errorhandler(ServiceUnavailable)
@app.errorhandler(AuthError)
def handle_db_down(error):
    return render_template("db_error.html", error=str(error)), 503


@app.route("/")
def home():
    driver = get_driver()
    mechanic = request.args.get("mechanic") or None
    theme = request.args.get("theme") or None

    games = queries.list_games(driver, mechanic=mechanic, theme=theme)
    all_mechanics = queries.list_mechanics(driver)
    all_themes = queries.list_themes(driver)

    return render_template(
        "index.html",
        games=games,
        all_mechanics=all_mechanics,
        all_themes=all_themes,
        selected_mechanic=mechanic,
        selected_theme=theme,
    )


@app.route("/game/<game_name>")
def game_detail(game_name):
    driver = get_driver()
    game = queries.get_game(driver, game_name)
    if game is None:
        abort(404)

    recommendations = queries.recommend_by_shared_mechanics(
        driver, game_name, min_shared=1
    )

    # Position nodes around the hub for the "connection web" SVG.
    # Hub sits at the center; each related game is placed on a circle
    # around it, spaced evenly by angle.
    web_nodes = []
    count = len(recommendations)
    for i, rec in enumerate(recommendations[:8]):  # cap for readability
        angle = (2 * math.pi * i / count) if count else 0
        radius = 150
        cx, cy = 220, 160
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        web_nodes.append(
            {
                "name": rec["recommended_game"],
                "shared_count": rec["shared_count"],
                "x": round(x, 1),
                "y": round(y, 1),
            }
        )

    return render_template(
        "game.html",
        game=game,
        recommendations=recommendations,
        web_nodes=web_nodes,
    )


@app.route("/connect", methods=["GET", "POST"])
def connect():
    driver = get_driver()
    all_games = [g["name"] for g in queries.list_games(driver)]

    path = None
    game_a = request.values.get("game_a") or None
    game_b = request.values.get("game_b") or None
    searched = False

    if game_a and game_b:
        searched = True
        if game_a == game_b:
            path = None
        else:
            path = queries.shortest_connection(driver, game_a, game_b)

    return render_template(
        "connect.html",
        all_games=all_games,
        game_a=game_a,
        game_b=game_b,
        path=path,
        searched=searched,
    )


@app.route("/designer/<designer_name>")
def designer_detail(designer_name):
    driver = get_driver()
    profile = queries.designer_theme_range(driver, designer_name)
    if profile is None:
        abort(404)
    return render_template("designer.html", profile=profile)


@app.errorhandler(404)
def not_found(error):
    return render_template("not_found.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
