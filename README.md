# redditSpyBot
A telegram bot that watches subreddits for particular post titles

### What does it do ###
Every 5 minutes it gets the newest posts for the specified subreddits and if the post titles match the regex then the telegram bot will notify the user.

### Features ###

* Supports watching of multiple subreddits at once
* Supports regex per subreddit
* Can also dump all text a user has written into reddit (comments/posts etc)
* Does not use [Praw](https://github.com/praw-dev/praw), hence no reddit credentials are required

### Python dependencies ###

* [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
* requests

## Installation

Install the dependencies:
```console
pip3 install -r requirements.txt
```

Generate a token for your bot by talking to the [Telegram bot father](https://t.me/botfather). Change the token in the source code to that of your bot.

Run bot:
```console
python3 bot.py
```

## Usage

* `/watch <subreddit name> <optional regex>` - Add subreddit to your watchlist. If regex is not provided, all posts will be matched. If subreddit is already on the watchlist, the regex will be updated
* `/unwatch <subreddit name>` - Remove subreddit from watchlist
* `/list` - Show all subreddits on the watchlist
* `/dump <reddit username>` - Gets all text a user has written in reddit and sends it as a text file
* `/enable` - Start polling subreddits on watchlist for posts every 5 minutes. (Disabled by default)
* `/disable` - Stop polling subreddits
* `/regshow <subreddit name>` - Show regex used for a particular subreddit
* `/regclear <subreddit name>` - Clear regex used for a subreddit to match all posts
* `/help` - Show help message
