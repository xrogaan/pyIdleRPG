#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:

import sys
import traceback
from time import sleep
import ../irclib
from ../ircbot import SingleServerIRCBot

irclib.DEBUG = 1

class TestBot(SingleServerIRCBot):
    def __init__(self):
        self.nickname = 'TestBot'
        self.server = [('88.191.66.146', 6667)]
        self.channels = ['#info']

    def our_start(self):
        SingleServerIRCBot.__init__(self, self.server, self.nickname,
                                    self.nickname)
        self.start()

    def on_welcome(self, c, e):
        print('Joining channels...')
        print(self.channels)
        c.join('#info')
        sleep(2)
        c.who('#info')
        sleep(8)
        print('-- DONE --')

    def on_whoreply(self, c, e):
        print(e.source())
        print(10*'-*'+'-')
        print(e.target())
        print(10*'-*'+'-')
        print(e.eventtype())
        print(10*'-*'+'-')
        print(e.arguments())


    def die(self):
        self.disconnect("I don't hate you")

b = TestBot()
msg = 'None'

try:
    b.our_start()
except KeyboardInterrupt, e:
    msg = 'Sanity level droping, disconnecting for you safety'
    pass
except SystemExit, e:
    msg = 'System going for maintenance, removing ongoing connections'
    pass
except:
    traceback.print_exc(file=sys.stdout)
    b.disconnect(msg)
    exit(0)

b.die()
