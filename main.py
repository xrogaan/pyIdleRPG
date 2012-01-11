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
from idlerpg import Characters

class IdleRPG(SingleServerIRCBot):
    # virtual events are commands that can be handled by the bot
    # privates= admins; public= anyone
    _privVirtualEvent = ['quit', 'doom']
    _pubVirtualEvent = ['whoami', 'register', 'login', 'logout',
                        'newpass', 'removeme', 'align', 'master',
                        'quest','help']
    owermask = []

    def __init__(self, config):
        self.settings = config
        self.db = Connection(**config['mongodb']).pyIdleRPG
        self.users = self.db['users']
        self.userBase = dict()
        self._gameChannel = None
        self.__ownermask = []
        # users schema: fullhost, nickname, password, characterName,
        #               email, loggedin
        # Todo: on channel join, ensure logged in status

    def our_start(self):
        SingleServerIRCBot.__init__(self, self.settings['servers'],
                                    self.settings['nickname'],
                                    self.settings['nickname'])
        self.start()

    def is_loggedIn(self, nickname):
        if self.userBase.has_key(nickname):
           if not self.userBase[nickname].empty:
               return True
        return False

    def daemon_increaseTTL(self, seconds):
        print("main.py:daemon_increaseTTL")
        for (nickname, user) in self.userBase.items():
            if not user.empty:
                r = user.increaseIdleTime(seconds)
                if r is not 1:
                    self.on_player_levelup(**r)

    def on_nicknameinuse(self, c, e):
        self.settings['nickname'] = c.get_nickname() + "_"
        c.nick(self.settings['nickname'])

    def on_welcome(self, c, e):
        print("Joining channels...")
        print(self.settings['channels'])
        for channel in self.settings['channels']:
            #There can only be one !
            if type(channel) is not type('') and self._gameChannel is None:
                channel = channel[0]
                self._gameChannel = channel
            c.join(channel)
            sleep(1)
        self.connection.execute_delayed(15, self.daemon_increaseTTL, [15],
                                        persistant=True)

    def on_join(self, c, e):
        nick = nm_to_n(e.source())
        channel = e.target()
        if nick == c.get_nickname() and channel == self._gameChannel:
            c.who(channel)

    def on_whoreply(self, c, e):
        """
        Will check every user on a given channel
        """
        print('main.py:on_whoreply()')
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
        channel = e.arguments()[0]
        nickname = e.arguments()[4]
        hostname = e.arguments()[2]
        username = e.arguments()[1]
        self.channels[channel].set_userdetails(nickname, [username, hostname])
        if not self.userBase.has_key(nickname):
            self.userBase[nickname] = Characters.Character(nickname,
                                                          hostname,
                                                          username,
                                                          self.users)

    def on_namreply(self, c, e):
        pass

    def on_action(self, c, e):
        self.on_pubmsg(c, e)

    def on_pubmsg(self, c, e):
        # will handle public messages
        source = nm_to_n(e.source())
        if not self.is_loggedIn(source):
            return
        if len(e.arguments()) == 1:
            body = e.arguments()[0]
            p = self.userBase[source].penalty(messagelenght=len(body))
            p = self.__nextLevelSentence(self.__int2time(p))
            c.privmsg(source, "Talking takes time, %s is added to your clock." % p)
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

        if not e.source() in self.__ownermask \
                and source in self.settings['owners']:
            self.__ownermask.append(e.source())
            print('Locked on %s. Waiting orders ...' % e.source())

        body = self.__cleanUpMsg(body)

        commands = body.split()
        commands[0] = commands[0].lower()

        if source in self.settings['owners']:
            virtualEvents = self._privVirtualEvent + self._pubVirtualEvent
        else:
            virtualEvents = self._pubVirtualEvent

        if commands[0] in virtualEvents:
            m = 'on_virt_' + commands[0]
            if hasattr(self, m):
                if self.userBase[source].empty and \
                        commands[0] not in ['login', 'help', 'register']:
                    c.privmsg(source, "You are not in the userbase.")
                    return
                getattr(self, m)(c, e)
            else:
                c.privmsg(source, "Sorry, this feature is not currently implemented")

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

    def on_virt_help(self, c, e):
        nick = nm_to_n(e.source())
        c.privmsg(nick, 'Keep dreaming.')

    # virtual events
    def on_virt_register(self, c, e):
        source = nm_to_n(e.source())
        if not self.userBase[source]:
            c.privmsg(source, 'You\'ve already got cookies.')
            return

        args = self.__getArgs(e)
        if len(args) < 4:
            c.privmsg(source, "Can't process request, 3 arguments needed.")
            c.privmsg(source, "usage: REGISTER <name> <password> <class> [<email>]")
            return -1

        charName, charPassword, charClass = args[1], args[2], args[3]
        if len(args) is 4:
            email = args[4]
            gender = 0
        else:
            gender, email = args[3], args[4]
            if gender not in [0,1,2]:
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
            c.privmsg(self._gameChannel, "Welcome to %s, the %s" % (charName,
                                                                    charClass))
        else:
            c.privmsg(source, "A problem occured resulting of your character "\
                              "not being registred")

    def on_virt_logout(self, c, e):
        # do a P20
        source = nm_to_n(e.source())
        self.userBase[source].P(20)
        self.userBase[source].unload()
        #del self.userBase[source]
        # We need the object
        #self.userBase[source] = Character()

    def on_virt_login(self, c, e):
        source = nm_to_n(e.source())
        args = self.__getArgs(e)
        if len(args)<3:
            c.privmsg(source, 'Not enough arguments.')
            return

        if not self.userBase[source].empty:
            c.privmsg(source, 'We also got icecream.') #not there
            return

        name, password = args[1], args[2]
        udetails = self.channels[self._gameChannel].userdict[source]
        if self.userBase[source].login_in(name, password) == 1:
            ttl = self.userBase[source].getTTL() - self.userBase[source].get_idle_time()
            c.privmsg(source, 'Welcome '+source+', '+name+' is up and running.')
            welcome = "%s, the level %d %s, is now online" \
                      "from nickname %s. Next level in %s" % (
                              name,
                              self.userBase[source].get_level(),
                              self.userBase[source].get_characterClass(),
                              source,
                              self.__nextLevelSentence(self.__int2time(ttl))
                              )
            c.privmsg(self._gameChannel, welcome)
        else:
            c.privmsg(source, "I couldn't find a match in the database. Please, check "\
                              "your credentials.")

    def on_virt_whoami(self, c, e):
        source = nm_to_n(e.source())
        # needs: charname, level, class, time to next level
        ttl=self.userBase[source].getTTL()-self.userBase[source].get_idle_time()
        charname = self.userBase[source].get_characterName()
        level = self.userBase[source].get_level()
        charclass = self.userBase[source].get_characterClass()
        nextl = self.__nextLevelSentence(self.__int2time(ttl))
        c.privmsg(source, "You are %s, the level %s %s. Next level in %s" % (
            charname,level, charclass, nextl))

    def on_virt_align(self, c, e):
        nick = nm_to_n(e.source())
        args = self.__getArgs(e)
        if len(args) == 1:
            c.privmsg(nick, "Not enough arguments.")
            return
        if args[1] == 'good':
            align = 1
        elif args[1] == 'neutral':
            align = 0
        elif args[1] == 'evil':
            align = -1
        else:
            c.privmsg(nick, "What you say ?")
            return
        self.userBase[source].set_alignment(align)
        c.privmsg(nick, 'Your alignment has been changed to %s' % args[1])

    def on_virt_removeme(self, c, e):
        source = nm_to_n(e.source())
        self.userBase[source].removeMe()
        del(self.userBase[source])
        details = self.channels[self._gameChannel][source]
        self.userBase[source] = Characters.Character(source, details[0], details[1],
                                          self.users, autologin=False)
        c.privmsg(source, 'Your character died of starvation.')

    def on_player_levelup(self, cname, level, nextl, cclass):
        nextl = self.__nextLevelSentence(self.__int2time(nextl))
        levelup_txt= "%s, the %s, has attained level %s! Next level in %s."
        self.connection.privmsg(self._gameChannel, levelup_txt % (cname, cclass, level, nextl))

    def __nextLevelSentence(self, time2level):
        if len(time2level) != 4:
            print("Error: __nextLevelSentence needs a tuple with 4 elements.")
            return
        return "%d days, %d hours, %d minutes and %d seconds" % time2level

    def __int2time(self, integer_time):
        """
        Compute a human readable time, translating the timestamp into days,
        hours, minutes and seconds. We probably don't want to fiddle with years.
        """
        from math import floor
        days, hours, minutes = 0, 0, 0
        if integer_time >= 86400:
            days = int(floor(integer_time / 86400))
            integer_time-= 86400*days
        if integer_time >= 3600:
            hours = int(floor(integer_time / 3600))
            integer_time-= 3600*hours
        if integer_time >= 60:
            minutes = int(floor(integer_time / 60))
            integer_time-= 60*minutes
        seconds = int(floor(integer_time))
        return (days, hours, minutes, seconds)

    def __removeColorCode(self, body):
        """
        Remove irc color char, leaving text untouch
        """
        # color char \x03nn,nnTEXT\x03
        if "\x03" in body:
            start = body.find('\x03')
            if start+1 == len(body):
                x = start+1
            for x in xrange(start+1, len(body)):
                if not ((start>0 and start+5-x<=start or start == 0 and start-x >= -5) \
                        and body[x].isdigit() or (body[x] is ',' and body[x+1].isdigit())):
                    break
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
        return event.arguments()[0].split(' ')

if __name__ == "__main__":
    import argparse
    import yaml
    parser = argparse.ArgumentParser(description="Another IdleRPG irc bot.")
    parser.add_argument('-s', '--server', metavar='SERVERNAME',
                        help='Server address to connect to')
    parser.add_argument('-p', '--port', metavar='PORT', default=6667,
                        help='Port number to connect to')
    parser.add_argument('-c', '--channel', metavar='CHANNEL',
                        help='Join CHANNEL on connect')
    parser.add_argument('-g', '--game-channel', action='store_true',
                        help='Set the CHANNEL as the game channel')
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
        if args.game_channel is not False:
            chan = [args.channel, 1]
        else:
            chan = args.channel
        config['channels'].append(chan)
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
