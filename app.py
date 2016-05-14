#!/usr/bin/env python3

# The MIT License (MIT)

# Copyright (c) 2016 RascalTwo @ therealrascaltwo@gmail.com

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import json
import time
import re
import logging
import logging.handlers
import requests
from datetime import datetime
from datetime import timedelta

class HTTPException(Exception):
    """Whenever there is a non-200 response code returned."""


class RedditAPIException(Exception):
    """Reddit itself returned a error based on our POST/GET request."""


def handle_response(response_expected):
    """Decorator to catch errors within request responses."""
    def wrap(function):
        def function_wrapper(*args, **kwargs):
            """Function wrapper."""
            response = function(*args, **kwargs)

            if response.status_code != 200:
                raise HTTPException("'{}' returned a status code of {}"
                                    .format(function.__name__,
                                            response.status_code))
            if response_expected == "json":
                data = response.json()
                if "errors" in data and len(data["errors"]) != 0:
                    raise RedditAPIException("\n".join("'{0}' error {1[0]}: {1[1]}"
                                                       .format(function.__name__, error)
                                                       for error in data["errors"]))

                if "error" in data:
                    raise RedditAPIException("'{}' error: {}"
                                             .format(function.__name__,
                                                     data["error"]))

                if "json" in data:
                    if "errors" in data["json"] and len(data["json"]["errors"]) != 0:
                        raise RedditAPIException("\n".join("'{0}' error {1[0]}: {1[1]}"
                                                           .format(function.__name__, error)
                                                           for error in data["json"]["errors"]))

                    if "error" in data["json"]:
                        raise RedditAPIException("'{}' error: {}"
                                                 .format(function.__name__,
                                                         data["json"]["error"]))


                return response.json()
            return response.text
        return function_wrapper
    return wrap


class IndianFoodFlairBot(object):

    def __init__(self):
        """Create bot and import 'config.json'."""
        with open("config.json", "r") as config_file:
            self.config = json.loads(config_file.read())

        self.token = None
        self.processed = []

    def _headers(self, auth=True):
        """Header(s) to send to Reddit.

        Keyword Arguments:
        `auth` (bool(true)) -- Should the 'Authorization' header be
                               included. Default is true. Options is provided
                               because '_get_token' must have this false.

        Returns:
        `dict` -- With keys as headers, and values as header contents.

        """
        if auth:
            return {
                "User-Agent": self.config["user_agent"],
                "Authorization": "{} {}".format(self.token["token_type"],
                                                self.token["access_token"])
            }
        return {
            "User-Agent": self.config["user_agent"]
        }

    @handle_response("json")
    def _get_token(self):
        """Return the access_token for this session.

        Returns:
        `dict` -- contains 'access_token', 'refresh_token', and 'token_type'.

        May throw a 'HTTPException' or 'RedditAPIException'.

        """
        client_auth = requests.auth.HTTPBasicAuth(self.config["client_id"],
                                                  self.config["client_secret"])
        post_data = {
            "grant_type": "password",
            "username": self.config["username"],
            "password": self.config["password"]
        }
        return requests.post("https://www.reddit.com/api/v1/access_token",
                             auth=client_auth,
                             data=post_data,
                             headers=self._headers(False))

    @handle_response("json")
    def _get_listing(self, url, count, after=""):
        return requests.get("{}?count={}&after={}".format(url, count, after),
                            headers=self._headers())

    def _get_all_listing_content(self, url, matching, oldest):
        content = []
        count = 0
        after = ""
        continue_listing = True
        while continue_listing:
            listing_data = self._get_listing(url, count, after)["data"]
            for listing in listing_data["children"]:
                if listing["data"]["created_utc"] < oldest:
                    continue_listing = False
                    break
                if listing["data"]["subreddit"].lower() != self.config["subreddit"].lower():
                    continue
                content.append(listing)
            if listing_data["after"] is None:
                continue_listing = False
            count += 25
            after = listing_data["after"]
        return content

    def refresh_token(self):
        """Attempt to refresh the access token."""
        try:
            self.token = self._get_token()
        except (HTTPException, RedditAPIException) as token_exception:
            self.token = None
            logger.critical("Could not get access token from the Reddit API.")
            logger.critical("This can be caused by mutiple things, such as:")
            logger.critical("  Reddit not being accessable")
            logger.critical("  Username and/or password being incorrect.")
            logger.critical("  'client_id' and/or 'client_secret' being incorrect.")
            logger.critical("  Applicaiton on Reddit not created as a 'script'.")
            logger.critical("Raw Error: {}".format(token_exception))

    def run(self):
        """Start the loop for the bot to run in."""
        self.refresh_token()

        uptime = 0

        while True:
            logger.info("Uptime: {}s".format(uptime))

            if self.token["expires_in"] <= 60:
                logger.info("Refreshing access token...")
                self.refresh_token()
                logger.info("Access token refreshed.")

            if uptime % self.config["check_rate"] == 0:
                try:
                    logger.info("Processing...")

                    csv = ""
                    for author in self.get_newest_authors():
                        csv += "\n"

                        counts = self.get_user_activity_counts(author)
                        flair = self.get_flair_for_user(author, counts)

                        if flair is None:
                            flair = {"text": "", "class": ""}

                        csv += "{},{},{}".format(author,
                                                 flair["text"],
                                                 flair["class"])

                    logger.info("Updating {} users.".format(len(csv.split("\n"))-1))

                    if csv != "":
                        self.set_user_flairs(csv)

                    if len(self.processed) > 200:
                        self.processed = self.processed[99:-1]

                    logger.info("Finished.")

                except(HTTPException, RedditAPIException) as exception:
                    logger.info("There was an error.")
                    logger.info("{}".format(exception))

            uptime += 60
            self.token["expires_in"] -= 60
            time.sleep(60)

    @handle_response("json")
    def get_newest_comments(self):
        return requests.get("https://oauth.reddit.com/r/{}/comments".format(self.config["subreddit"]),
                            headers=self._headers())

    @handle_response("json")
    def get_newest_posts(self):
        return requests.get("https://oauth.reddit.com/r/{}/new".format(self.config["subreddit"]),
                            headers=self._headers())

    def get_newest_authors(self):
        authors = []

        content = self.get_newest_comments()["data"]["children"]
        content.extend(self.get_newest_posts()["data"]["children"])

        for item in content:
            if item["data"]["name"] in self.processed:
                continue
            self.processed.append(item["data"]["name"])
            if item["data"]["author"] in authors or item["data"]["author"] in self.config["ignored_users"]:
                continue
            authors.append(item["data"]["author"])

        return authors

    def get_user_activity_counts(self, username):
        activities = {
            "comment": 0,
            "post": 0
        }
        for activity in self._get_all_listing_content("https://oauth.reddit.com/user/{}"
                                                      .format(username),
                                                      {"subreddit": "IndianFood"},
                                                      time.time() - self.config["rules_rate"]):
            if activity["kind"] == "t1":
                activities["comment"] += 1
            elif activity["kind"] == "t3":
                activities["post"] += 1

        return activities

    @handle_response("json")
    def set_user_flairs(self, csv):
        post_data = {
            "flair_csv": csv
        }
        return requests.post("https://oauth.reddit.com/r/{}/api/flaircsv"
                             .format(self.config["subreddit"]),
                             data=post_data,
                             headers=self._headers())

    def get_flair_for_user(self, author, counts):
        choices = {
            "comment": None,
            "post": None
        }

        for rule in self.config["rules"]:
            if rule["min"] <= counts[rule["type"]] and counts[rule["type"]] <= rule["max"]:
                choices[rule["type"]] = rule

        if choices["post"] is None:
            return choices["comment"]

        if choices["comment"] is None:
            return choices["post"]

        return choices["comment"] if choices["comment"]["weight"] > choices["post"]["weight"] else choices["post"]


if __name__ == "__main__":
    logging_format = logging.Formatter("[%(asctime)s] [%(levelname)s]: %(message)s")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    file_logger = logging.handlers.TimedRotatingFileHandler("logs/output.log", when="midnight", interval=1)
    file_logger.setFormatter(logging_format)
    logger.addHandler(file_logger)

    console_logger = logging.StreamHandler()
    console_logger.setFormatter(logging_format)
    logger.addHandler(console_logger)

    IndianFoodFlairBot().run()
