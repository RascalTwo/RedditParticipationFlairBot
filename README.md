# Reddit /r/IndianFood Flair Bot

Made for /u/asliyoyo to set the flairs of users on /r/IndianFood based on the ammount of posts and comments made by them in a range of time.

Requires `username`, `password`, `client_id`, and `client_secret` for the Reddit account the bot will run under.

Also requires the account to have moderator status in the subreddit of which the sidebar will be updated, as the bot assigns flairs..

# Dependencies

- [Python 3](https://www.python.org/download/releases/3.0/)
- [Requests](http://docs.python-requests.org/en/master/)

You can have the dependencies automatically installed by executing `pip install -r requirements.txt`, although there is only one dependency. You will obviously have to obtain Python and pip manually.

# Setup

## Reddit Account

Go the `Apps` tab of your reddit account preferences.

![reddit-prefs](https://i.imgur.com/fA33kDv.png)

Give it a name of whatever you want - you can change this later - and a redirect URL of `http://127.0.0.1:6504/authorize_callback`. You won't need to use this for this bot, it just requires this field to be filled out. Also make sure to mark it as a `Script`.

![app-creating](https://i.imgur.com/s44fMdw.png)

You'll then see the ID and secret of the application. You enter these in the `client_id` and `client_secret` fields. They are marked red and green respectively.

![app-details](https://i.imgur.com/hydS5CT.png)

You will also need to fill out the empty fields in the `config.json` accordinly. You should have text before the forward slash & version number in the `user_agent` field be the same as the app name you created.

That's all the setup required for the app. You can now exeute the script and it should work.

## Configuration

The configuration file - `config.json` looks like this:

```json
{
    "client_id": "",
    "client_secret": "",
    "user_agent": "SomethingUnique/1.0 by /u/Rascal_Two for /u/asliyoyo running under /u/{BOT_NAME} at /r/IndianFood",
    "username": "",
    "password": "",
    "subreddit": "IndianFood",
    "check_rate": 60,
    "rules_rate": 604800,
    "rules": [
        {
            "name": "Casual Reader",
            "type": "comment",
            "text": "",
            "class": "chai",
            "min": 5,
            "max": 10,
            "weight": 0
        }
    ],
    "ignored_users": [
        "AutoModerator"
    ]
}
```

- `client_id` is the client ID of the reddit application setup above.
- `client_secret` is the cllicne secret of the reddit application setup above.
- `user_agent` is what reddit identifies the bot as. The more unique this is the better, as common user agents have their rates limited.
- `username` is the username of the Reddit account the bot will run under.
- `password` is the password of the Reddit account the bot will run under.
- `subreddit` is the name of the subreddit sidebar that's being updated.
- `check_rate` is the rate of time - in seconds - that the bot will check for new comments and posts, and calculate the flairs for the new authors.
- `rules_rate` is the rate of time - in seconds - that the rules are enforeced by. It is defaulty set to one week, meaning that users posts and comments are counted a week into the past.
- `rules` is the list of actual flair rules.
- `ignored_users` is a list of users who to ignore. These users will never be counted nor have their flairs changed.
*****

A rule has seven properties:

- `name` is the name of the rule. It has no impact asside from organizing the rules while configuring
- `type` can be either `comment` or `post`, and determines if the flairs is based on the number of posts or comments made in `rules_rate`.
- `text` is the text label of the flair that would be set.
- `class` is the css class of the flair that would be set.
- `min` is the minimum amount of posts/comments required for the user to make to obtain this flair.
- `max` is the maximum amount of posts/comments required for the user to make to obtain this flair.
- `weight` is more of an internal setting. It is intended to be used when the user can be given two applicable flairs, the flair with the higher weight is the one the user gets.

Weight Example:

> A user has made enough posts and comments to be applicable for both `Casual Commentator` and `Casual Contributor`.

> Which flair should the user have?

> Well `Casual Commentator` has a `weight` of `1`, while `Casual Contributor` has a weight of `1.5`.

> The user gets the `Casual Contributor` flair.

# Explanation

When the bot is first created it loads the configuration data from the `config.json` file. It then sends the `username`, `password`, `client_id`, and `client_secret` to the Reddit API to get a access token. This access token lasts 60 minutes, and is used to do actions as the reddit account.

This access token is automatically refreshed, so the bot can run for a very long time.

Every minute it outputs a message stating it's uptime. It also checks if it's time to recalculate the flairs of the newest authors.

*****

If it it, then it counts all the newest authors of `new` and `comments`. Each author has all their posts and comments counted.

The new flairs for the authors are calculated based on the number of posts and comments, and then the flairs are changed.

*****

# TODO

> I may do some of these, I may do none of these. Depends on how worth-it said feature would be.

- Convert to [PRAW](https://praw.readthedocs.io/en/stable/)
