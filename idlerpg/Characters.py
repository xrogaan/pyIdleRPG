# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:
"""
TEST check on __init__ if the player is already connected.
TODO load when needed some character ifno
TODO load important info such as: identify chains

schema of the code:
Character:
    equipment
    body

    __init__(cname, chost, cequipment, cbody)
    updateBodyPart(bodyPartId, +/-Float, Collection)
    updateEquipment(equipmentKey, +/-Int, Name=None, Collection)
"""

from hashlib import sha1
from types import *
from time import time

def validateEmail(email):
    import re
    if len(email) > 6:
        if (re.match('^[a-zA-Z0-9._%-+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$',
            email) != None):
            return 1
    return 0

class Character:
    _equipmentKeys = ['leggings', 'tunic', 'weapon', 'ring', 'shield',
                     'amulet', 'helm', 'charm', 'boots', 'gloves']
    #Not used yet
    _bodyPartKeys = ['hips', 'vagina', 'cock', 'breasts', 'tallness', 'hair',
                     'face', 'ear', 'antennae', 'horns', 'wings', 'lowerbody']


    def __init__(self, nickname, hostname, username, myCollection,
                 password=None, cname=None):
        self.empty = True
        self.nickname = nickname
        self.hostname = hostname
        self.equipment = {}
        self._mother = talkBack
        self._myCollection = myCollection

        if cname is None:
            cdata = self._myCollection.find_one({'nickname': self.nickname,
                                                 'hostname': self.hostname,
                                                 'username': self.username,
                                                 'loggedin': True})
            if len(cdata) == 0:
                return -1
            method='autoload'
        else:
            cdata = self._myCollection.find_one({'character_name': cname:
                                                'password': sha1(password)})
            method='loggin'

        self.initialized_at = time()
        self.load(cdata,method)

    def load(self, characterData, method):
        """
        Load userdata in memory
        """
        if method == 'loggin':
            toUpdate = {}
            if characterData['nickname'] is not self.nickname:
                toUpdate.update({'nickname': self.nickname})
                characterData['nickname'] = self.nickname
            if characterData['hostname'] is not self.hostname:
                toUpdate.update({'hostname': self.hostname})
                characterData['hostname'] = self.hostname
            if len(toUpdate) > 0:
                self._myCollection.update({'_id': characterData['_id']},
                                    {'$set': toUpdate})

        self._myId = characterData['_id']
        # TODO verify if loading the equipment in memory is really needed
        for key in self._equipmentKeys:
            if not characterData['equipment'].has_key(key):
                pass
            val = characterData['equipment'][key]
            self.equipment.update({key: val})

        self.characterName = characterData['character_name']
        self.registeredat = characterData['registeredat']
        self.idle_time = characterData['idle_time']
        self.total_idle = characterData['total_idle']
        self.level = characterData['level']
        self.empty = False
        return 1

    def unload(self):
        """
        Commit everything into the database
        """
        data = {'total_idle': self.total_idle,
                'level': self.level,
                'idle_time': self.idle_time}

        self._myCollection.update({'_id': self._myId},
                {'$set': data})
        return 1

    def createNew(self, myCollection, cname, password, email, gender=0):
        if self.empty is not True:
            return -1

        # Do not use email if
        if validateEmail(email) < 1:
            email=None

        # find twins
        haveTwin = myCollection.find_one({'character_name': cname})
        if haveTwin is not None:
            return 0

        from os.path import exists
        from hashlib import sha1
        import yaml
        import random
        import time

        if len(int(gender))>1 or (gender is 0 or gender is not in [1,2]):
            gender = random.randrange(1,2)

        password = sha1(password).hexdigest()

        with file('character.yaml','r') as stream:
            myCharacter = yaml.load(stream)

        myCharacter.save({'character_name': cname,
                            'nickname': self.nickname,
                            'hostname': self.user_host,
                            'password': password,
                            'email': email,
                            'gender': gender,
                            'level': 1,
                            'registeredat': time.time()
                            'ttl': self._ttl(1)
                            })
        self._myId = myCollection.insert(myCharacter)
        return 1

    def getTTL(self, level=None):
        """
        return the Time To Level for a specified level
        """
        level = level if level is not None else self.level
        return int(600*(1.16**level))

    def getLevel(self, idletime=None):
        idletime = idletime if idletime is not None else self.total_idle
        level = 1
        while idletime > -1:
            idletime-= self.getTTL(level)
            level+=1
        return level

    def getEquipmentSum(self):
        data = self._myCollection().find(
                {'_id': self._myId},
                {'_id': 0, 'equipment': 1})
        esum = sum([item['power'] for item in data['equipment'].itervalues()])
        return esum

    def levelUp(self):
        self.level+= 1
        self.idle_time = 0
        self._myCollection.update({'_id': self.myId},
                                   {'$inc': {'level': 1
                                             'total_idle': self.idle_time},
                                    '$set': {'idle_time': 0,
                                             'ttl': self._ttl()}}
                                  )
        return 1

    def rename(self, newName):
        if self.empty:
            return 0
        self._myCollection.update({'character_name': self.characterName},
                                   {'$set': {'character_name': newName})
        self.characterName = newName

    def penalty(self, penalty=0, messagelenght=None):
        """
        increment the time to idle to next level by M*(1.4**LEVEL)
        """
        if self.empty:
            return 0
        if messagelenght is not None and int(messagelenght) > 0:
            incrase = messagelenght * (1.14**int(self.level))
        else:
            incrase = int(penalty) * (1.14**int(self.level))
        self._myCollection.update({'character_name': self.characterName},
                                   {'$inc': {'ttl': incrase})
        return penalty

    def P(self, modifier):
        """
        alias for self.penalty
        """
        return self.penalty(penalty=modifier)

    def updateBodypart(self, bodypID, value):
        mname = '__update_' + bodypID
        if hasattr(self, mname):
            o = getattr(self, mname)(value)
        else:
            pass

    def updateEquipment(self, equipKey, value, name=None):
        updateValue = {'equipment.'+equipKey: {'power': value, 'name': name}}
        self._myCollection.update({'character_name': self.characterName,
                                   'equipment.'+equipKey+'.power': {'$lt': value}},
                                  updateValue,
                                  false)
        # TODO: Checking the Outcome of an Update Request
        # http://www.mongodb.org/display/DOCS/Updating#Updating-CheckingtheOutcomeofanUpdateRequest
        self.equipment[equipKey] = (value, name)


    def get_characterName(self):
        return self.characterName

    def get_nickname(self):
        return self.nickname

    def get_hostname(self):
        return self.user_host

    def get_equipment(self, key=None):
        if key is not None:
            return self.equipment.get(key, 0)
        else:
            return self.equipment.items()
