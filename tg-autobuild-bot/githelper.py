#!/usr/bin/env python
import logging
import os
import shutil
import subprocess

from git import Repo
from git.exc import GitCommandError

import mysqlHelper as db
from config import (gitusername, gitpassword)

logger = logging.getLogger(__name__)


def clone(bot, message, updateMessage, sendFile):
	"""Method to clone/pull and build the repo"""
	repoURL = db.getrepocloneurl(message.chat_id, gitusername, gitpassword)
	repoDir = db.getrepodir(message.chat_id)
	if not os.path.isdir(repoDir):
		"""The repo isnt cloned yet. Let's clone it first"""
		try:
			Repo.clone_from(repoURL, repoDir)
		except GitCommandError as e:
			e = str(e)
			if "Authentication failed" in e:
				updateMessage(message, "Git Authentication error")
			elif "Repository not found" in e:
				updateMessage(message, "Repo not found! Check your remote repository and try again!")
			else:
				updateMessage(message, "unknown error")
			return False
		updateMessage(message, "repo cloned")
		"""The repo exists already. Let's just pull the latest source"""
	else:
		updateMessage(message, "Repo syncing...")
		try:
			Repo(repoDir).remote().pull()
		except GitCommandError as e:
			e = str(e)
			if "exit code(1)" in e:
				print "Error pulling repo"
			return False

	# time.sleep(5)
	updateMessage(message, "Building apk...")
	"""Build the apk. Returns the result - True/False and the apk path if the result is True"""
	result, apkLocation = buildapk(repoDir)
	if not result:
		updateMessage(message, "Building apk failed...")
		return False
	"""Send the apk to the chat"""
	updateMessage(message, "Sending apk...")
	sendFile(bot, message.chat_id, apkLocation)
	"""Update the hash to latest commit hash to check if the app should be built again
	if there is no new commits in the upstream"""
	db.updatehash(message.chat_id, getLatestRemoteHash(repoDir))
	return True


def buildapk(repodir):
	"""Build the apk, sign and copy the signed apk to /outputs directory with the commit hash appended to the file name.
	Redirect all the gradle errors to error.log file"""
	try:
		output = subprocess.check_output(
			"cd " + repodir + " && chmod +x gradlew && ./gradlew assembleRelease --stacktrace 2> error.log", shell=True)
		if "BUILD SUCCESSFUL" in output:
			apkPath = subprocess.check_output('find  -name "app-release.apk"', shell=True)
			if apkPath.rstrip() == '':
				"""Probably apk signing failed"""
				logger.info("APK not available")
				return False, None
			subprocess.check_output('mkdir -p ' + repodir + '/output', shell=True)
			apkDestLocation = destApkLocation(repodir)
			shutil.move(apkPath.rstrip(), apkDestLocation)
			return True, apkDestLocation
		return False, None
	except subprocess.CalledProcessError as e:
		print "error code", e.returncode
		if e.returncode is not 0:
			return False, None
	return False, None


def destApkLocation(repodir):
	"""Return the location where the apk must be copied to"""
	appName = repodir.rpartition('/')[2]
	cmd = '{0}/output/{1}-{2}.apk'.format(repodir, appName, getLatestRemoteHash(repodir))
	return cmd


def getLatestRemoteHash(repodir):
	"""Get the latest hash of the upstream repo"""
	try:
		output = subprocess.check_output("cd " + repodir + " && git rev-parse --short HEAD",
											shell=True)  # , "&&", "git", "rev-parse --short HEAD)"])
		return output.rstrip()
	except Exception as e:
		return ""
