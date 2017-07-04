#!/usr/bin/env python
import logging

import requests, os
from requests.auth import HTTPBasicAuth
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.ext.dispatcher import run_async

import githelper as git
import mysqlHelper as db
from config import botapiToken, botUserName, gitusername, gitpassword
from mwt import MWT

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


@MWT(timeout=60)
def get_admin_ids(bot, chat_id):
	"""Method to get list of admins of a group cached every minute"""
	return [admin.user.id for admin in bot.get_chat_administrators(chat_id)]


def is_admin(message, userid=None):
	"""Method to check if the user is an admin. Returns True by default if everyone in the group is admin or the
	chat is private"""
	if userid is None:
		userid = message.from_user.id

	if message.chat.all_members_are_administrators:
		return True
	elif message.chat.type in (message.chat.GROUP,  message.chat.SUPERGROUP) and userid in \
			get_admin_ids(message.bot, message.chat_id):
		return True
	elif message.chat.type in (message.chat.PRIVATE):
		return True
	else:
		return False


def setadminonly(bot, update):
	"""Command handler method to set if the /build command must only be used by admin."""
	msg = update.message
	print type(msg.chat_id)
	if not msg.chat.type == msg.chat.PRIVATE and not is_admin(msg):
		msg.reply_text("You think you have permission to do this? Grow up!")
		return

	keyboard = [[InlineKeyboardButton("Yes!", callback_data="setadmin-true%{}".format(msg.from_user.id)),
				InlineKeyboardButton("No", callback_data="setadmin-false%{}".format(msg.from_user.id))]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	update.message.reply_text("should the build command be invoked by admins only?", reply_markup=reply_markup)


def start(bot, update, args):
	"""Command handler method to start conversation with the bot. Required if the chat is private"""
	if len(args) > 0:
		"""Check if there is a payload with the start command to send the log in private"""
		params = args[0].split("_")
		if params[0] == "sendlog":
			logpath = db.getlogfile(params[1])
			if os.path.isfile(logpath) and os.path.getsize(logpath) > 0:
				update.message.reply_text("sending log")
				sendFile(bot, update.message.chat_id, logpath)
			else:
				update.message.reply_text("No log found")
			return
	update.message.reply_text('Hello World!')


def hello(bot, update):
	"""Command handler method to display hello message"""
	update.message.reply_text(
		'Hello {}!\nTry /help to find the list of possible commands and its actions!'.format(update.message.from_user.first_name))


def getchatid(bot, update):
	"""Command handler method to get the chatid of the group(To debug)"""
	update.message.reply_text(update.message.chat_id)


def forceBuild(bot, update):
	"""Command handler method to force build the repo though the repo with latest source has already been built.
	Is strictly admin only to prevent server load. If successful, calls build() with force=True"""
	msg = update.message
	if not is_admin(msg):
		msg.reply_text("You think you have permission to do this? Grow up!")
		return
	compilerepo(bot, update, force=True)


@run_async
def compilerepo(bot, update, force=False):
	"""Command handler method to sync the source, build and send the apk to the chat"""
	message = update.message
	chat_id = message.chat_id
	commit_hash = db.getlatesthash(chat_id)

	"""Check if admins only are allowed to run the command"""
	if db.isadminonly(chat_id) and not is_admin(message):
		message.reply_text("Only admins can build repo!")
		return

	"""If no /forcebuild is called, there is no need to build the repo again if the latest source is already built.
	Check if the lastest source is build and inform the user"""
	if not force and commit_hash == git.getLatestRemoteHash(db.getrepodir(chat_id)):
		# msg = update.message.reply_text("App already built")
		keyboard = [[InlineKeyboardButton("Yes!", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]]
		reply_markup = InlineKeyboardMarkup(keyboard)
		message.reply_text(
			"An already built app is available for the latest source.\nDo you want to send the app?",
			reply_markup=reply_markup)
		return
	if force:
		msg = message.reply_text("Force building app")
	else:
		msg = message.reply_text("Repo cloning...")
	try:
		if db.getRepo(chat_id) == '':
			"""OOPS! if the code reaches this point, the user tried to /build without setting the repo url!"""
			msg.edit_text("No repo set. Set a repo using /setrepo first")
			return
		"""This is where the actual build occurs! The return value is a boolean"""
		result = git.clone(bot, msg, updatemessage, sendFile)
		if not result:
			"""Oops! Building app failed for some reason! Ask the user if the error log must be sent.
			If yes, it is sent in a private chat"""
			if message.chat.type == message.chat.PRIVATE:
				keyboard = [[InlineKeyboardButton("Send", callback_data="err-log-send"),
							InlineKeyboardButton("Don't send", callback_data="err-log-dntsend")]]
			else:
				"""Called when the chat is not private. This lets the log to be sent in private than in the group"""
				keyboard = [[InlineKeyboardButton("Send",
													url="https://telegram.me/{0}?start=sendlog_{1}".format(botUserName,
													chat_id),
													callback_data="err-log-msg-update"),
							InlineKeyboardButton("Don't send", callback_data="err-log-dntsend")]]
			reply_markup = InlineKeyboardMarkup(keyboard)
			msg.edit_text(text="Build failed")
			message.reply_text("An error has occured while building the app. Do you want me to send the log?",
										reply_markup=reply_markup)
	except Exception as w:
		logger.info(w)


def button(bot, update):
	"""Method to handle callback data from inlinekeyboard buttons"""
	query = update.callback_query
	message = query.message
	"""Yes - If /build is called and if there is a app build from the latest source already and the user press yes to send 
	the app again, send it. 
	No - Else edit the keyboard to consume the action
	err-log-send - If build failed and the chat is private
					and the user selected yes to send the log, send it in private chat
					by calling start with payload from the web call
	err-log-dntsend - If the build failed and the user selected no, update the inlinekeyboard to consume the action
	setadmin-true - set only admins can call /build to True. Will be consumed only if the choice is made by an admin
	setadmin-false - set only admins can call /build to False. Will be consumed only if the choice is made by an admin"""
	if query.data == "yes":
		bot.edit_message_text("App is being sent!", chat_id=message.chat_id, message_id=message.message_id)
		repoDir = db.getrepodir(message.chat_id)
		sendFile(bot, message.chat_id, git.destApkLocation(repoDir))
	elif query.data == "no":
		bot.edit_message_text("Ok! The app wont be sent", chat_id=message.chat_id,
								message_id=message.message_id)
	elif query.data == "err-log-send":
		bot.edit_message_text("Log is being sent", chat_id=message.chat_id, message_id=message.message_id)
		sendFile(bot, message.chat_id, db.getlogfile(message.chat_id))
	elif query.data == "err-log-msg-update":
		bot.edit_message_text("Log is being sent in private", chat_id=message.chat_id,
								message_id=message.message_id)
		print "updating mesage"
	elif query.data == "err-log-dntsend":
		bot.edit_message_text("Log will not be sent", chat_id=message.chat_id,
								message_id=message.message_id)
	elif "setadmin-true" in query.data:
		print "inside set"
		if is_admin(message, int(query.data.rpartition("%")[2])):
			db.setadminonly(message.chat_id, True)
			bot.edit_message_text("Only admins can execute /build from now on!", chat_id=message.chat_id,
								message_id=message.message_id)
		else:
			print "isadmin failed"
	elif "setadmin-false" in query.data:
		if is_admin(message, int(query.data.rpartition("%")[2])):
			db.setadminonly(message.chat_id, False)
			bot.edit_message_text("Anyone can execute /build from now on!", chat_id=message.chat_id,
								message_id=message.message_id)


def updatemessage(message, new_text_message):
	"""Method to update a message with new text"""
	try:
		message.edit_text(text=new_text_message)
	except Exception as e:
		logger.info(e)


def sendFile(bot, chat_id, pathToFile):
	"""Method to send a file to the chat (apk, log)"""
	bot.send_document(chat_id=chat_id, document=open(pathToFile, 'rb'))


def unknown(bot, update):
	"""If the user sends a command which is not recognized by the bot, inform the user"""
	update.message.reply_text("Sorry, I didn't understand that command.\nTry /help to get available commands")


def help(bot, update):
	"""Command handler method to send the supported commands by the bot"""
	update.message.reply_text(
		'Hello there!Try the below commands!\n'
		'/start - Initialize the bot\n'
		'/setrepo [{github username}/{repository}] - set the github repository to use to build apk\n'
		'/getrepo - Get the repo used for building apk\n'
		'/setadminonly - Provides a inline button keyboard to set if the build command can only be used by admins\n'
		'/build - Build the app from latest source pulled from remote repository\n'
		'/forcebuild - Force a build though latest app from source is built already(Admins only!)\n'
		'/chatid - Get your unique chat id(For debugging)')


def setrepo(bot, update, args):
	"""Command handler to set the repo to use to build the app. This method is strictly admin only"""
	msg = update.message
	if not is_admin(msg):
		msg.reply_text("You think you have permission to do this? Grow up!")
		return
	chat_id = msg.chat_id

	"""Check if there is any arguments passed with /setrepo if not, inform user to send command with one.
	The arugument must contain a github repo link in the form GITHUB_USER/REPONAME"""
	if not len(args) > 0:
		msg.reply_text("Oops! no option specified!\nSyntax is /setrepo [{github username}/{repo}]")
		return
	chatargs = str(args[0])

	"""Make sure the argument is not empty"""
	if chatargs.strip() in (None, ''):
		msg.reply_text("Oops! The option cannot be empty\nSyntax is /setrepo [{github username}/{repo}]")
		return

	"""Build the repo url with chat args"""
	url = 'https://github.com/' + chatargs
	gitapiurl = 'https://api.github.com/repos/'
	httpauth = None

	"""Check if github username and password is set in config.py.
	If yes, authenticate to github api with the credentials"""
	if not gitusername == '' and not gitpassword == '':
		httpauth = HTTPBasicAuth(gitusername, gitpassword)
	data = requests.get(gitapiurl + chatargs, auth=httpauth).json()

	"""Check the response json for errors. If the repo url is present in the result, the repo is valid.
	If not found, either repo does not exist or is private and credentials is not provided to access it"""
	if "Not Found" in data.values():
		result = "Oops! Seems like the repo doesnt exist!\nMake sure the repo link is correct, follows the required" \
					" format and is public."
	elif "Bad credentials" in data.values():
		result = "Oops! Seems like the git credentials is not correct! Please check the credentials and try again!"
	elif (url + ".git").lower() in (str(x).lower() for x in data.values()):
		result = db.addRepo(chat_id, chatargs)
	else:
		result = "Unknown error has occured! Could not verify the repo existence"
	msg.reply_text(result)


def getrepo(bot, update):
	"""Command handler to display the set repo"""
	update.message.reply_text("The repo url is {}".format(db.getrepourl(update.message.chat_id)))


def error_callback(bot, update, error):
	"""Method to handle default telegram errors"""
	try:
		raise error
	except Unauthorized:
		# remove update.message.chat_id from conversation list
		print (Unauthorized)
	except BadRequest:
		# handle malformed requests - read more below!
		print (BadRequest)
	except TimedOut:
		# handle slow connection problems
		print (TimedOut)
	except NetworkError:
		# handle other connection problems
		print (NetworkError)
	except ChatMigrated as e:
		# the chat_id of a group has changed, use e.new_chat_id instead
		db.updateID(update.message.chat_id, e.new_chat_id)
	except TelegramError:
		# handle all other telegram related errors
		print (TelegramError)


def main():
	"""Main method where the bot is initialized and all the supported commands, error handlers are added for listening"""
	updater = Updater(token=botapiToken)
	updater.dispatcher.add_handler(CommandHandler('start', start, pass_args=True))
	updater.dispatcher.add_handler(CommandHandler('hello', hello))
	updater.dispatcher.add_handler(CommandHandler('chatid', getchatid))
	updater.dispatcher.add_handler(CommandHandler('build', compilerepo))
	updater.dispatcher.add_handler(CommandHandler('forcebuild', forceBuild))
	updater.dispatcher.add_handler(CallbackQueryHandler(button))
	updater.dispatcher.add_handler(CommandHandler('help', help))
	updater.dispatcher.add_handler(CommandHandler("setrepo", setrepo, pass_args=True))
	updater.dispatcher.add_handler(CommandHandler('getrepo', getrepo))
	updater.dispatcher.add_handler(CommandHandler('setadminonly', setadminonly))
	updater.dispatcher.add_handler(MessageHandler(Filters.command, unknown))
	updater.dispatcher.add_error_handler(error_callback)

	updater.start_polling()
	updater.idle()


if __name__ == '__main__':
	main()
