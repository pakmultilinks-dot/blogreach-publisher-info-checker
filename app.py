# -*- coding: utf-8 -*-
"""
BlogReach: Publisher Website Info Checker.

A small Flask tool. Enter a website URL and see its page title, meta
description, HTTPS usage, load time, and homepage link count.

Fully stateless, so it runs on serverless platforms (Vercel) as well as
normal servers.

Run locally:
    pip install -r requirements.txt
    python app.py
"""
import os

from dotenv import load_dotenv
from flask import Flask, request, render_template

from checker import InvalidURLError, UnreachableError, check_website

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", result=None, error=None, url="")


@app.route("/check", methods=["POST"])
def check_route():
    url = request.form.get("url", "")
    try:
        result = check_website(url)
    except InvalidURLError as exc:
        return render_template("index.html", result=None, error=str(exc), url=url)
    except UnreachableError as exc:
        return render_template("index.html", result=None, error=str(exc), url=url)
    return render_template("index.html", result=result, error=None, url=url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
