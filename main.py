#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:

version= 0,1,0

import sys
import traceback
from time import sleep, time

from ircbot import SingleServerIRCBot
from irclib import nm_to_n, nm_to_uh, nm_to_h
from pymongo import Connection, GEO2D

class IdleRPG(SingleServerIRCBot):
    # virtual events are commands that can be handled by the bot
    # privates= admins; public= anyone
    _privVirtualEvent = ['quit', 'doom']
    _pubVirtualEvent = ['whoami', 'register', 'login', 'logout',
                        'newpass', 'removeme', 'align', 'status',
                        'quest']
    owermask = []

    def __init__(self, config):
        self.settings = config
        self.db = Connection().pyIdleRPG
        self.users = self.db['users']
        self.userBase = dict()
        self._gameChannel = ''
        # users schema: fullhost, nickname, password, characterName,
        #               email, loggedin
        # Todo: on channel join, ensure logged in status

    def our_start(self):
        SingleServerIRCBot.__init__(self, self.settings['servers'],
                                    self.settings['nickname'],
                                    self.settings['nickname'])
        self.start()

    def _initialysePlayers(self, channel):
        ch = self.channels[channel]
        for (nickname, details) in ch.userdict.iteritems():
            self.userBase[nickname] = Character(nickname,
                                                details[0],
                                                details[1],
                                                self.users)

    def is_loggedIn(self, nickname):
        if self.userBase.has_key(nickname):
           if self.userBase[nickname] is not -1:
               return True
        return False

    def daemon_increaseTTL(self, seconds):
        for (nickname, user) in self.userBase.iteritems():
            if not user.empty:
                user.increaseTTL(seconds)

    def on_nicknameinuse(self, c, e):
        self.settings['nickname'] = c.get_nickname() + "_"
        c.nick(self.settings['nickname'])

    def on_welcome(self, c, e):
        print("Joining channels...")
        print(self.settings['channels'])
        for channel in self.settings['channels']:
            if type(channel) is not type(''):
                channel = channel[0]
                self._gameChannel = channel
            c.join(channel)
            sleep(1)
            if (channel is self._gameChannel):
                c.who(channel)
                self._initialysePlayers(channel)
#            c.names(chan) # will trigger a namreply event
        self.execute_delayed(15, self.daemon_increaseTTL, 15)

    def on_whoreply(self, c, e):
        """
        Will check every user on a given channel
        """
        # ['#info', 'youple',
        # 'Voyageur-d8235afd822dbcbb3d7f3197785647294ab8941.wanadoo.fr',
        # 'irc.multimondes.net', 'w0lfy', 'H', '0 boum']
        #
        # e.arguments()[0] = channel
        # e.arguments()[1] = username
        # @
        # e.arguments()[2] = userhost
        # e.arguments()[3] = server
        # e.arguments()[4] = nickname
        nickname = e.arguments()[4]
        hostname = e.arguments()[2]
        username = e.arguments()[1]
        self.channel.set_userdetails(nickname, [username, hostname])

    def on_namreply(self, c, e):
        pass

    def on_pubmsg(self, c, e):
        # will handle public messages
        source = nm_to_n(e.source())
        if not self.is_loggedIn(source):
            return
        if len(e.arguments()) == 1:
            body = e.arguments()[0]
            self.userBase[source].penalty(messagelenght=len(body))
        elif e.arguments()[0] == 'ACTION': # ctcp ACTION
            body = source + " " + e.arguments()[1]
        else: # ignore everything else
            return

    def on_privmsg(self, c, e):
        # will handle private messages
        source = nm_to_n(e.source())
        if len(e.arguments()) == 1:
            body = e.arguments()[0]
        else:
            return

        if not e.source() in self.ownermask and source in self.owners:
            self.ownermask.append(e.source())
            print('Locked on %s. Waiting orders ...' % e.source())

        body = self.cleanUpMsg(body)

        commands = body.split()
        commands[0] = commands[0].lower()

        if source in self.owners:
            virtualEvents = self._privVirtualEvent + self._pubVirtualEvent
        else:
            virtualEvents = self._pubVirtualEvent

        if commands[0] in virtualEvents:
            m = 'on_virt_' + commands[0]
            if hasattr(self, m):
                getattr(self, m)(c, e)
            else:
                c.privmsg(source, """Sorry, this feature is not currently
                        implemented""")

        eventtype = c
        method = "on_" + eventtype

    def on_part(self, c, e):
        # do a P350 if logged in
        source = nm_to_n(e.source())
        if self.is_loggedIn(source):
            self.userBase[source].P(350)

    def on_quit(self, c, e):
        # do a P30 if logged in
        source = nm_to_n(e.source())
        if self.is_loggedIn(source):
            self.userBase[source].P(30)

    # virtual events
    def on_virt_register(self, c, e):
        source = nm_to_n(e.source())
        if self.userBase[source] is not -1:
            c.privmsg('You\'ve already got cookies.')
            return

        args = self.__getArgs()
        if len(args) < 4:
            return -1

        charName, charPassword, charClass = args[0], args[1], args[2]
        if len(args) is 4:
            email = args[3]
            gender = 0
        else:
            gender, email = args[3], args[4]
            if gender is not in [0,1,2]:
                gender = 0

        template = {'character_name': charName,
                    'character_class': charClass,
                    'nickname': source,
                    'password': charPassword,
                    'email': email,
                    'gender': gender,
                    'hostname': nm_to_h(e.source())}

        answer = self.userBase[source].createNew(self.users, **template)
        if answer is 1:
            c.privmsg(source, "You've been successfully registred. You can now login.")

    def on_virt_logout(self, c, e):
        # do a P20
        source = nm_to_n(e.source())
        self.userBase[source].P(20)
        self.userBase[source].unload()
        del self.userBase[source]
        self.userBase[source] = -1

    def on_virt_login(self, c, e):
        source = nm_to_n(e.source())
        args = self.__getArgs()
        if len(args)<3:
            c.privmsg(source, 'Not enough arguments.')
            return

        if self.userBase[source] is -1:
            c.privmsg(source, 'We also got icecream.')
            return

        name, password = args[1], args[2]
        udetails = self.channels[self._gameChannel].userdict[source]
        self.userBase[source] = Character(source,
                                          udetails[0],
                                          udetails[1],
                                          self.users,
                                          cname=name,
                                          password=password)
        c.privmsg(source, 'Welcome '+source+'.')

    def __removeColorCode(self, body):
        """
        Remove irc color char if it's starting a chain
        """
        # remove irc color char \x03nn,nnTEXT\x03
        if "\x03" in body:
            start = body.find('\x03')
            if start+1 == len(body):
                x = start+1
            for x in xrange(start+1, len(body)):
                if not ((start>0 and start+5-x<=start or start == 0 and start-x >= -5) \
                        and body[x].isdigit() or (body[x] is ',' and body[x+1].isdigit())):
                    break
    #        if start == 0:
    #            body = body[:start] + body[x:]
    #        else:
            body = body[:start] + body[x:]
            body = self.__removeColorCode(body)
        return body

    def __cleanUpMsg(self, body):
        body = self.__removeColorCode(body)
        #remove special irc fonts chars
        body = body.replace("\x02",'')
        body = body.replace("\xa0",'')
        return body

    def __getArgs(self, event):
        return event.arguments()[0].split('')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Another IdleRPG irc bot.")
    parser.add_argument('-s', '--server', metavar='SERVERNAME',
                        help='Server address to connect to')
    parser.add_argument('-p', '--port', metavar='PORT', default=6667,
                        help='Port number to connect to')
    parser.add_argument('-c', '--channel', metavar='CHANNEL',
                        help='Join CHANNEL on connect')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set the verbosity level to verbose')
    parser.add_argument('configFile', metavar='CONFIG', nargs='?',
                        type=argparse.FileType('r'),
                        help='Configuration parameters in yaml format')
    args = parser.parse_args()

    if args.configFile is not None:
        config = yaml.load(args.configFile.read())
        config.setdefault('channels', [])
        config.setdefault('owners', [])
        config.setdefault('nickname', 'pyIdleRPG')
        config.setdefault('verbose', args.verbose)
    else:
        config = {'servers': [],
                  'channels': [],
                  'nickname': 'pyIdleRPG',
                  'verbose': args.verbose}

    if args.server is not None:
        config['servers'].append((args.server, args.port))
    elif len(config['servers']) == 0:
        parser.error('No server configured.')

    if args.channel is not None:
        config['channels'].append(args.channel)
    elif len(config['channels']) == 0:
        argumentParser.error('No channel configured.')

    myBot = IdleRPG(config)

    try:
        myBot.our_start()
    except KeyboardInterrupt, e:
        myBot.settings['quitmsg'] = "Bot ended by keyboard request."
        pass
    except SystemExit, e:
        myBot.settings['quitmsg'] = "System going for maintenance."
        pass
    except:
        traceback.print_exc()
        # try to disconnect
        myBot.disconnect()
        exit(0)

    myBot.disconnect('EOF')
