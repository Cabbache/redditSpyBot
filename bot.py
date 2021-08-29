#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

import logging
import requests
import datetime
import json
import re
import os
from io import StringIO
from html.parser import HTMLParser

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, PicklePersistence, Filters, MessageHandler

# Enable logging
logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

def getrequest(url):
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT x.y; rv:10.0) Gecko/20100101 Firefox/10.0'
	}
	res = requests.get(url, headers=headers)
	return res.text

class MLStripper(HTMLParser):
	def __init__(self):
		super().__init__()
		self.reset()
		self.strict = False
		self.convert_charrefs= True
		self.text = StringIO()
	def handle_data(self, d):
		self.text.write(d)
	def get_data(self):
		return self.text.getvalue()

def strip_tags(html):
	s = MLStripper()
	s.feed(html)
	return s.get_data()

def sublink(sub_name):
	return '<a href="https://reddit.com/r/'+sub_name+'">r/'+sub_name+'</a>'

def findSubByName(subreddits, subreddit):
	matches = [sub for sub in subreddits if sub['name'] == subreddit]
	if len(matches):
		return matches[0]
	return None
 
#https://stackoverflow.com/questions/15940280/how-to-get-utc-time-in-python
def secondsToText(seconds, granularity=2):
	intervals = (
		('weeks', 24*7*60**2),
		('days', 24*60**2),
		('hours', 60**2),
		('minutes', 60),
		('seconds', 1),
	)
	result = []

	for name, count in intervals:
		value = seconds // count
		if value:
			seconds -= value * count
			if value == 1:
				name = name.rstrip('s')
			result.append("{} {}".format(value, name))
	return ', '.join(result[:granularity])

def reddit_poll(context: CallbackContext) -> None:
	info = context.job.context
	udata = info['context'].user_data
	reply = ""

	if "subreddits" not in udata:
		return

	for subreddit in udata["subreddits"]:
		res = getrequest("https://reddit.com/r/"+subreddit['name']+"/new.json?limit=15")
		posts = json.loads(res)
		if 'error' in posts:
			print("reddit returned error: " + posts['message'])
			continue

		childs = posts['data']['children']
		postids = [child['data']['id'] for child in childs]
		print("ids obtained: " + str(postids))
		print("ids remembered: " + str(subreddit['ids']))
		
		newposts = set(postids) - set(subreddit['ids'])
		reply += "\n".join([
			(
				"r/%s - "
				"[<a href='https://www.reddit.com/u/%s'>%s</a>]: "
				"<a href='https://www.reddit.com%s'>%s</a>"
			) % (subreddit['name'], post['data']['author'], post['data']['author'], post['data']['permalink'], post['data']['title'])
			for post in childs
			if post['data']['id'] in newposts and
			re.search(subreddit['regex'], post['data']['title'], re.IGNORECASE) is not None
		])

		if len(subreddit['ids']) == 0:
			reply = ""

		subreddit['ids'] = postids
	
	if not reply:
		return
	
	reply = "matched post:\n" + reply
	context.bot.send_message(info['chat_id'], text=reply, parse_mode=ParseMode.HTML)

def enable(update: Update, context: CallbackContext) -> bool:
	current_jobs = context.job_queue.get_jobs_by_name("reddit_poll")
	if current_jobs:
		update.message.reply_text("Already enabled")
		return False

	context.job_queue.run_repeating(
		reddit_poll,
		first=1,
		interval=300,
		context={
			'context': context,
			'chat_id': update.message.chat_id
		}
	)

	update.message.reply_text('Reddit polling enabled')
	return True

def watch_subreddit(update: Update, context: CallbackContext) -> bool:
	try:
		subreddit = context.args[0]
		if strip_tags(subreddit) != subreddit or re.search(r"[a-zA-Z0-9_-]+", subreddit) is None:
			raise ValueError('Invalid subreddit name')
		if "subreddits" not in context.user_data:
			context.user_data["subreddits"] = []
		esub = findSubByName(context.user_data["subreddits"], subreddit)
		if esub is not None and len(context.args) == 1:
			update.message.reply_text("It is already in your watchlist. use /regclear to clear regex")
			return False
		regex = ""
		if len(context.args) > 1:
			regex = " ".join(context.args[1:])
			try:
				re.compile(regex)
			except re.error:
				update.message.reply_text("Invalid regex expression")
				return False
		if esub is None:
			response = getrequest("https://www.reddit.com/r/"+subreddit)
			if "Sorry, there aren’t any communities on Reddit with that name." in response:
				update.message.reply_text("Subreddit does not exist")
				return False
			context.user_data["subreddits"].append({
				'name': subreddit,
				'ids': [],
				'regex': regex
			})
			update.message.reply_text("Added "+sublink(subreddit)+" to your watchlist", parse_mode=ParseMode.HTML)
		else:
			esub["regex"] = regex
			update.message.reply_text("Updated regex for r/"+subreddit)
		return True
	except (IndexError, ValueError):
		update.message.reply_text("Usage: /watch <subreddit name> <optional regex>")
		return False

def clear_regex(update: Update, context: CallbackContext) -> bool:
	try:
		subreddit = context.args[0]
		sub = findSubByName(context.user_data["subreddits"], subreddit)
		if sub is None:
			update.message.reply_text("subreddit not in watchlist")
			return False
		sub["regex"] = ""
		update.message.reply_text("regex cleared for r/" + sub["name"])
		return True
	except (IndexError):
		update.message.reply_text("Usage: /regclear <subreddit name>")
		return False

def show_regex(update: Update, context: CallbackContext) -> bool:
	try:
		subreddit = context.args[0]
		sub = findSubByName(context.user_data["subreddits"], subreddit)
		if sub is None:
			update.message.reply_text("subreddit not in watchlist")
			return False
		if sub["regex"]:
			update.message.reply_text(sub["regex"])
		else:
			update.message.reply_text("No regex is set")
		return True
	except (IndexError):
		update.message.reply_text("Usage: /regshow <subreddit name>")
		return False

def remove_subreddit(update: Update, context: CallbackContext) -> bool:
	try:
		subreddit = context.args[0]
		if "subreddits" not in context.user_data:
			update.message.reply_text(sublink(subreddit) + " was not in the watchlist", parse_mode=ParseMode.HTML)
			return False
		index = next((i for i, item in enumerate(context.user_data["subreddits"]) if item['name'] == subreddit), None)
		if index is None:
			update.message.reply_text(sublink(subreddit) + " was not in the watchlist", parse_mode=ParseMode.HTML)
			return False
		context.user_data["subreddits"].pop(index)
		update.message.reply_text("removed "+sublink(subreddit)+" from watchlist", parse_mode=ParseMode.HTML)
		return True
	except (IndexError):
		update.message.reply_text("Usage: /unwatch <subreddit name>")
		return False

def list_subreddits(update: Update, context: CallbackContext) -> None:
	if "subreddits" not in context.user_data or len(context.user_data['subreddits']) == 0:
		update.message.reply_text("No subreddits on watchlist")
		return
	message = "Subreddits on your watchlist:\n"
	message += '\n'.join([
		sublink(x['name'])+": "+(x['regex'] if x['regex'] else "*all post titles*")
		for x in context.user_data["subreddits"]])
	update.message.reply_text(message, parse_mode=ParseMode.HTML)

def dump_user_data(update: Update, context: CallbackContext) -> bool:
	try:
		username = context.args[0]
		#TODO strip username
		jsontext = getrequest("https://api.reddit.com/user/"+username+"/submitted?limit=99999999")
		dump = json.loads(jsontext)
		if "error" in dump:
			if dump["error"] == 404:
				update.message.reply_text("No such reddit user")
			else:
				update.message.reply_text("reddit returned error: "+dump["message"])
			return False
		text = "\n".join([
			child['data']['title']+child['data']['selftext'] for child in dump['data']['children']
		])
		jsontext = getrequest("https://api.reddit.com/user/"+username+"/comments?limit=99999999")
		dump = json.loads(jsontext)
		if "error" in dump:
			update.message.reply_text("reddit returned error: "+dump["message"])
			return False
		text += "\n".join([
			child['data']['body'] for child in dump['data']['children']
		])
		dumpfilename = "dump_"+username+".txt"
		with open(dumpfilename, "w") as dd:
			dd.write(text)
		
		context.bot.sendDocument(
			update.message.chat_id,
			document=open(dumpfilename, "rb")
		)
		os.remove(dumpfilename)

		accountinfo = getrequest(
			"https://api.reddit.com/user/"+username+"/about"
		)
		dump = json.loads(accountinfo)
		age = (
			(datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()
		) - int(dump['data']['created_utc'])
		update.message.reply_text("Account "+username+" is "+secondsToText(age)+" old")
		return True
	except(IndexError, ValueError):
		update.message.reply_text("Usage: /dump <reddit username>")
		return False

def disable(update: Update, context: CallbackContext) -> bool:
	dis = disableByName("reddit_poll", context)
	if dis:
		update.message.reply_text("reddit polling disabled")
	else:
		update.message.reply_text("Already disabled")
		
def disableByName(name: str, context: CallbackContext) -> bool:
	current_jobs = context.job_queue.get_jobs_by_name(name)
	if not current_jobs:
			return False
	for job in current_jobs:
			job.schedule_removal()
	return True

def help_command(update: Update, context: CallbackContext) -> None:
	update.message.reply_text(
		"/list - show subreddits on your watchlist\n"
		"/watch <subreddit name> <optional regex> - watch latest posts on the specified subreddit that have their title matching the regex\n"
		"/unwatch <subreddit name> - remove subreddit form watchlist\n\n"
		"/regclear <subreddit name> - change regex of subreddit to empty\n"
		"/regshow <subreddit name> - show regex applied for subreddit\n\n"
		"/dump <reddit username> - Get all text a user has written into reddit\n\n"
		"/enable - start polling subreddits for new posts every 5 minutes\n"
		"/disable - stop polling subreddits"
	)

def main() -> None:
	# Create the Updater and pass it your bot's token.
	persistence = PicklePersistence(filename='bot_data')
	bot_token = "Change this" #Change this
	updater = Updater(bot_token, persistence=persistence)

	# Get the dispatcher to register handlers
	dispatcher = updater.dispatcher

	# on different commands - answer in Telegram
	dispatcher.add_handler(CommandHandler("enable", enable))
	dispatcher.add_handler(CommandHandler("disable", disable))
	dispatcher.add_handler(CommandHandler("watch", watch_subreddit))
	dispatcher.add_handler(CommandHandler("unwatch", remove_subreddit))
	dispatcher.add_handler(CommandHandler("watchlist", list_subreddits))
	dispatcher.add_handler(CommandHandler("list", list_subreddits))
	dispatcher.add_handler(CommandHandler("dump", dump_user_data))
	dispatcher.add_handler(CommandHandler("regclear", clear_regex))
	dispatcher.add_handler(CommandHandler("regshow", show_regex))
	dispatcher.add_handler(MessageHandler(Filters.all, help_command))

	# Start the Bot
	updater.start_polling()

	# Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
	# SIGABRT. This should be used most of the time, since start_polling() is
	# non-blocking and will stop the bot gracefully.
	updater.idle()

if __name__ == '__main__':
		main()
