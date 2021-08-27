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
