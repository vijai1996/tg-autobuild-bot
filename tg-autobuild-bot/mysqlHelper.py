#!/usr/bin/env python
import MySQLdb
import logging

from config import (dbhost, dbuser, dbpass, dbname, dbtablename)

logger = logging.getLogger(__name__)


def connect():
	"""Method to open a mysql connection"""
	return MySQLdb.connect(host=dbhost,  # your host, usually localhost
							user=dbuser,  # your username
							passwd=dbpass,  # your password
							db=dbname)


def addRepo(chatid, url):
	"""Method to add or update the repo for the chatid"""
	db = connect()
	cursor = db.cursor()
	querychatid = "select id from " + dbtablename + " where chatid=%s"
	updatechatid = "update " + dbtablename + " set url=%s where chatid=%s"
	insertsql = "insert into " + dbtablename + " (chatid,url) values (%s, %s)"
	try:
		cursor.execute(querychatid, (chatid,))
		if cursor.rowcount > 0:
			cursor.execute(updatechatid, (url, chatid))
			result = "The repo url has been successfully updated to {}".format("https://github.com/" + url)
		else:
			cursor.execute(insertsql, (chatid, url))
			result = "The repo url has been successfully set to {}".format("https://github.com/" + url)
		db.commit()
	except Exception as e:
		logger.info(e)
		result = "Could not set repo url. Please try again later"
	finally:
		db.close()
	return result


def getRepo(chatid):
	"""Get the repo set for the chatid from database"""
	db = connect()
	cursor = db.cursor()
	try:
		cursor.execute("select url from " + dbtablename + " where chatid=%s", (chatid,))
		row = cursor.fetchone()
		if row is None:
			return ""
		else:
			return row[0]
	except Exception as e:
		logger.info(e)
		return None
	finally:
		db.close()


def getrepourl(chatid):
	"""Get repo from the getRepo() method and build full repo url"""
	repo = getRepo(chatid)
	if repo is None:
		return "Could not retrieve repo. Try again later"
	elif repo == '':
		return " null.\nPlease set one using /setrepo"
	else:
		return "{}".format("https://github.com/" + repo)


def getrepocloneurl(chatid, username, password):
	"""Method to generate and return github url formatted with the username and password. """
	repo = getRepo(chatid)
	if repo is None:
		return None
	elif repo == '':
		return ''
	else:
		return "https://{0}:{1}@github.com/{2}".format(username, password, repo)


def getlatesthash(chatid):
	"""Get the hash of the last build"""
	db = connect()
	cursor = db.cursor()
	commit_hash = ""
	try:
		cursor.execute("select commit_hash from " + dbtablename + " where chatid=%s", (chatid,))
		row = cursor.fetchone()
		commit_hash = row[0]
	except Exception as e:
		logger.info(e)
	finally:
		db.close()
	return commit_hash


def updatehash(chat_id, new_hash):
	"""Update the hash of the built repo in database"""
	db = connect()
	cursor = db.cursor()
	try:
		cursor.execute("update " + dbtablename + " set commit_hash=%s where chatid=%s", (new_hash, chat_id))
		db.commit()
	except Exception as e:
		logger.info(e)
	finally:
		db.close()


def updateID(old_chat_id, new_chat_id):
	"""Update the chat id if it changes"""
	db = connect()
	cursor = db.cursor()
	try:
		cursor.execute("update " + dbtablename + " set chatid=%s where chatid=%s", (new_chat_id, old_chat_id))
		db.commit()
	except Exception as e:
		logger.info(e)
	finally:
		db.close()


def setadminonly(chat_id, option):
	"""Method to set adminonly column in database to True/False"""
	db = connect()
	cursor = db.cursor()
	try:
		cursor.execute("update " + dbtablename + " set adminonly=%s where chatid=%s", (option, chat_id))
		db.commit()
	except Exception as e:
		logger.info(e)
	finally:
		db.close()


def isadminonly(chat_id):
	"""Method to get if adminonly column from database. Returns True/False"""
	db = connect()
	cursor = db.cursor()
	try:
		cursor.execute("select adminonly from " + dbtablename + " where chatid=%s", (chat_id,))
		row = cursor.fetchone()
		return bool(row[0])
	except Exception as e:
		logger.info(e)
	finally:
		db.close()


def getrepodir(chat_id):
	"""Returns the directory to which the repo will be cloned"""
	repoURL = getRepo(chat_id)
	repoName = repoURL.rpartition("/")[2]
	return "repos/" + repoName


def getlogfile(chat_id):
	"""Returns the log file for the repo from chatid"""
	return getrepodir(chat_id) + "/error.log"
