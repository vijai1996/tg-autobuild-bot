# tg-autobuild-bot
A telegram bot for automatic building, signing and send android apps from github source

## Table of Contents
1. [Introduction](#Introduction)
2. [Usage](#Usage)
3. [Supported Commands](#supported-commands)
4. [Support](#support)
5. [Contributing](#contributing)
6. [Donations](#donations)
7. [License](#license)

## Introduction
**Tg-autobuild-bot** is a python telegram bot built for easy automatic cloning, building and signing of OpenSource android apps stored on github either on private or public repository. The bot relies on the gradle system for building and signing the app. The bot currently works only on linux but could be made to work for windows too! (PR welcome). A couple of commands is all it takes to command the bot to build the apk and send it to the chat the command was initiated on!

## Usage
There is [wiki pages](wiki) to setup the bot and run the bot on any server. If you are still stuck, you can always contact me for further help

## Supported Commands
The list of commands supported by the bot:
```
/start - Initialize the bot
/setrepo [{github username}/{repository}] - set the github repository to use to build apk
/getrepo - Get the repo used for building apk
/setadminonly - Provides a inline button keyboard to set if the build command can only be used by admins
/build - Build the app from latest source pulled from remote repository
/forcebuild - Force a build though latest app from source is built already(Admins only!)
/chatid - Get your unique chat id(For debugging)
```

## Support
For support you can:
1. create issue in repository 
2. Join the support group in telegram at [@autobuildbotsupport](https://telegram.me/autobuildbotsupport)
3. Mail me at [contact@orpheusdroid.com](mailto:contact@orpheusdroid.com)

## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

## Donations
#### Bitcoin:     1Cbf61y8XNx3BLWvoZB71x4XgBKB7r8BuB
#### PayPal:      [![Paypal Donate](https://www.paypalobjects.com/webstatic/en_US/i/btn/png/gold-pill-paypal-26px.png)](https://paypal.me/vijaichander/5)

## License
This project is licensed under the GNU AGPL v3.0 License - see the [LICENSE](LICENSE) file for details
