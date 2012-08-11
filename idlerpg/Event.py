# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:
"""
Data stored in the database depends on even type

Event types:
    * quests (different quest type, see wiki)
    * object ecounters
    * monster ecounters
    * calamities
    * hand of gods
    * godsend

handofgod:
    text: "%s god blessed by ..."

clock: internal clock. Something happen every clock second.
"""

import logging
from pymongo import Database

class Event(object):
    def __init__(self, clock, etype, **kwargs):
        """
        * clock should be the rate at which the game ticks (global config)
        * etype is the event type (listed in EventMasterList)
        * kwargs should contain information about the player list and access
          to the character objects
        """
        self._logger = logging.getLogger('Event.Event')
        self.clock = clock
        self.etype = etype
        self._odds = 0
        self.options = kwargs
        return 1

    @properties
    def odds(self):
        from random import randint
        return randint(0, (self._odds*86400)/self.clock)

    @odds.setter
    def odds(self, value):
        value = int(value)
        if value < 1:
            value = 1
            self._logger.warn('odds must be greater or equal to 1.')
        self._odds = value

    @odds.deleter
    def odds(self):
        del self._odds

    def get_text(self):
        return self.text

class CalamityEvent(Event):
    def __init__(self, clock, etype, kwargs):
        super(CalamityEvent, self).__init__(clock, etype, kwargs)
        self.odds = self.options['odds']
        self._messages = self.options['msg']

    def message(self):
        from random import randint
        n = randint(0, len(self._messages))
        return self._messages[n]

class HogEvent(Event):
    """
    * move a player forward or backward in time by a fraction of the user total
      idle
    * one in five chance to trigger bad outcome

    """
    def __init__(self, clock, etype, kwargs):
        super(HogEvent, self).__init__(clock, etype, kwargs)

    def message(self):
        return ''

# trigger improvements onto player
class GodsendEvent(Event):
    pass

class EncounterEvent(Event):
    pass

class MonsterEncounter(Encounter):
    pass

# once the inventory is properly done
class ObjectFind(Encounter):
    pass

class EventMasterList(object):
    """
    Contain a list of every event.
    """

    def __init__(self, databaseObj, config):
        self._types = ('calamity', 'hog', 'godsend', 'object_find',
                       'monster_encounter')
        self._documentObj = databaseObj.events
        self._events = dict()
        for calamity in self._documentObj.find({'etype':'calamity'}):
            if not self._events.has_key('calamity'):
                self._events.update({'calamity': list()})
            self._events['calamity'].append(Event(clock=config.clock,
                                                  etype='calamity',
                                                  **calamity))

class EventManager(object):
    version = 1.0
    def __init__(self, databaseObj, config):
        self._logger = logging.getLogger('Event.EventManager')
        if not isinstance(databaseObj, Database):
            self._logger.error('Require an instance of '\
                               'pymongo.database.Database to work. Got %s.',
                               type(databaseObj))
        self._databaseObj = databaseObj
        self._eventsObj = databaseObj.events

        version = self._eventsObj.find_one({}, {'version':1})
        if not version:
            self.__start_install()
        elif float(version) < self.version:
            self.__start_upgrade(version)

        self._master = EventMasterList(self._databaseObj, config)

    def __start_install(self):
        pass

    def __start_upgrade(self, version):
        method = '__upgrade_from_' + version + '_to_' + self.version
        if not hasattr(self, method):
            self._logger.critical('The Event collection upgrade failed: '\
                                  "I don't know how to upgrade from %0.2f "\
                                  'to %0.2f.', (version, self.version))
            raise RuntimeError('Collection upgrade failed.')
        getattr(self, method)(version)

    def trigger(self):
        pass
