"""
Bubbly & Ammu — Flask server
Serves the game pages as simple static routes.

Run it:
    pip install flask
    python app.py

Then open:
    http://localhost:5000/          -> home page
    http://localhost:5000/rps       -> Stone, Paper, Scissors game
    http://localhost:5000/maze      -> the maze game
    http://localhost:5000/sudoku    -> the sudoku game
"""

from flask import Flask, render_template, send_from_directory, abort
import os

app = Flask(__name__)

PARENT_DIR = os.path.join(os.path.dirname(__file__), "..")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/rps")
def rps():
    return send_from_directory(PARENT_DIR, "sps.html")


@app.route("/maze")
def maze():
    return send_from_directory(PARENT_DIR, "game.html")


@app.route("/sudoku")
def sudoku():
    return send_from_directory(PARENT_DIR, "sudoku.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
