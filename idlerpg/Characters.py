# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:
"""
Equipment data format:
    {'equipment': [{'type': 'boots', 'name': 'Leather Boots', 'power': 10}]}
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
                 autologin=True):
        self.empty = True
        self.nickname = nickname
        self.hostname = hostname
        self.username = username
        self.equipment = {}
        self._myCollection = myCollection

        if autologin is False:
            return

        cdata = self._myCollection.find_one({'nickname': self.nickname,
                                             'hostname': self.hostname,
                                             'username': self.username,
                                             'loggedin': True})
        if type(cdata) is type(None):
            return
        if len(cdata) > 0:
            self.empty = False
            self.load(cdata,'autoload')

    def __db_update(self, spec, document):
        res = self._myCollection.update(spec, document, safe=True)
        return res['updatedExisting']

    def login_in(self, character_name, password):
        cdata = self._myCollection.find_one({
            'character_name': character_name,
            'password': sha1(password).hexdigest()
            })

        if cdata is not None and len(cdata) > 0:
            self.empty = False
            self.load(cdata, 'loggin')
            return 1
        return -1

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
                characterData.update(toUpdate)

        self._myId = characterData['_id']
        # equipment shouldn't be None, but just in case.
        if characterData['equipment'] is None:
            characterData['equipment'] = []
        # TODO verify if loading the equipment in memory is really needed
        for item in characterData['equipment']:
            if item['type'] not in self._equipmentKeys:
                # uh ho, I don't know that kind of item ...
                pass
            self.equipment.update({item['type']: {'name': item['name'],
                                                  'power': item['power']}})

        del(characterData['equipment'])
        self.characterData = characterData
        self.empty = False
        return 1

    def unload(self):
        """
        Commit everything into the database
        """
        data = {'total_idle': self.characterData['total_idle'],
                'level': self.characterData['level'],
                'idle_time': self.characterData['idle_time']}

        self._myCollection.update({'_id': self._myId},
                {'$set': data})
        self.characterData = {}
        self.equipment = {}
        self.empty = True
        self._myId = None
        return 1

    def removeMe(self):
        self._myCollection.remove({'_id': self._myId})
        self.characterData = {}
        self.equipment = {}
        self._myId = None
        self.empty = True

    def createNew(self, myCollection, character_name, character_class,
                        nickname, hostname, password, email, gender=0,
                        align=0):
        if self.empty is not True:
            return -1

        # Do not use email if
        if validateEmail(email) < 1:
            email=None

        # find twins
        haveTwin = myCollection.find_one({'character_name': character_name})
        if haveTwin is not None:
            return 0

        from os.path import exists
        from hashlib import sha1
        import yaml
        import random

        if int(gender) not in [1,2]:
            gender = random.randrange(1,2)

        password = sha1(password).hexdigest()

        with file('include/character.yaml','r') as stream:
            myCharacter = yaml.load(stream)

        myCharacter.update({'character_name': character_name,
                            'nickname': nickname,
                            'hostname': hostname,
                            'password': password,
                            'email': email,
                            'gender': gender,
                            'character_class': character_class,
                            'level': 1,
                            'registeredat': time(),
                            'ttl': self.getTTL(1),
                            'idle_time': 0,
                            'total_idle': 0,
                            'alignment': 0 if align not in [-1,0,1] else align
                            })
        self._myId = myCollection.insert(myCharacter)
        return 1

    def increaseIdleTime(self, ittl):
        cttl = self.getTTL()
        if cttl <= self.characterData['idle_time']+ittl:
            # LEVEL UP
            self.levelUp()
            nttl = self.characterData['idle_time']+ittl - self.characterData['idle_time']
            self._myCollection.update({'_id': self._myId},
                    {'$inc': {'idle_time': nttl, 'total_idle': ittl}})
            return {'level': self.characterData['level'], 'nextl': self.getTTL(),
                    'cname': self.get_characterName(), 'cclass': self.get_characterClass()}
        else:
            self._myCollection.update({'_id': self._myId},
                    {'$inc': {'idle_time': ittl, 'total_idle': ittl}})
            self.characterData['idle_time']+=ittl
            return 1

    def getTTL(self, level=None):
        """
        return the Time To Level for a specified level or return the
        current ttl from the database.
        """
        if level is None:
            return self._myCollection.find_one({'_id': self._myId}, {'ttl': 1})['ttl']
        else:
            return int(600*(1.16**level))

    def getEquipmentSum(self):
        data = self._myCollection.find_one(
                {'_id': self._myId},
                {'equipment': 1})
        return sum([item['power'] for item in data['equipment']])

    def levelUp(self):
        self.characterData['level']+= 1
        self._myCollection.update({'_id': self._myId},
                                   {'$inc': {'level': 1,
                                             'total_idle': self.characterData['idle_time']},
                                    '$set': {'idle_time': 0,
                                             'ttl': self.getTTL(self.characterData['level'])}}
                                  )
        self.characterData['idle_time'] = 0
        return 1

    def rename(self, newName):
        if self.empty:
            return 0
        self._myCollection.update({'_id': self._myId},
                                   {'$set': {'character_name': newName}})
        self.characterData['character_name'] = newName

    def penalty(self, penalty=0, messagelenght=None):
        """
        increment the time to idle to next level by M*(1.4**LEVEL)
        """
        if self.empty:
            return 0
        if messagelenght is not None and int(messagelenght) > 0:
            penalty = int(messagelenght)

        increase = int(penalty) * (1.14**int(self.characterData['level']))
        self._myCollection.update({'_id': self._myId},
                                   {'$inc': {'ttl': increase}})
        return increase

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
        res = self._myCollection.update(
            {
                '_id': self._myId,
                'equipment.'+equipKey+'.power': {'$lt': value}
            },
            {
                '$set': {
                    'equipment.'+equipKey+'.power': value,
                    'equipment.'+equipKey+'.name': name
                    }
                }, safe=true)
        if res['updatedExisting'] is False:
            return -1
        # TODO: Checking the Outcome of an Update Request
        # http://www.mongodb.org/display/DOCS/Updating#Updating-CheckingtheOutcomeofanUpdateRequest
        self.equipment[equipKey] = (value, name)
        return 1

    def get_gender(self):
        return self.characterData['gender']

    def get_characterClass(self):
        return self.characterData['character_class']

    def get_characterName(self):
        return self.characterData['character_name']

    def get_nickname(self):
        return self.nickname

    def get_hostname(self):
        return self.user_host

    def get_level(self):
        return self.characterData['level']

    def get_ttl(self):
        """
        return the time to level. Alias of getTTL
        """
        return self.getTTL()

    def get_idle_time(self):
        return self._myCollection.find_one({'_id':self._myId},
                                           {'idle_time': 1})['idle_time']

    def get_alignment(self):
        return self.characterData['alignment']

    def get_equipment(self, key=None):
        if key is not None:
            return self.equipment.get(key, 0)
        else:
            return self.equipment.items()

    def set_alignment(self, align):
        """
        Return True if the alignment could be changed
        Return -1 if the argument doesn't fit
        Return False if the update process fail (this is really bad)
        """
        if align not in [-1,0,1]:
            return -1
        return self.__db_update(
                {'_id': self._myId},
                {'$set': {'alignment': align}})

    def set_gender(self, gender):
        if int(gender) not in [1, 2]:
            return -1
        return self.__db_update(
                {'_id': self._myId},
                {'$set':{'gender': gender}})

    def set_email(self, email):
        if validateEmail(email) is 1:
            return self.__db_update(
                    {'_id': self._myId},
                    {'$set': {'email': email}})

    def set_password(self, password, oldpassword):
        return self.__db_update(
                {
                    '_id': self._myId,
                    'password': sha1(oldpassword).hexdigest()
                    },
                {'password': sha1(password).hexdigest()})


"""
head:
    eye[color, size]
    ear[shape, size]
    horn[shape, size]
    hairs[size, color]
"""
class Anatomy:
    def __init__(self):
        self.eyes_type = None
        self.eyes_color = None
        self.horns = None
        self.hair_lenght = None
        self.hair_color = None
        self.wing_type = None
        self.ear_type = None
        self.horn_type = None
        self.horns_type = None
        self.face_type = 1
        self.antennae = None
        self.leg_type = 1 # 1. human; 2. demonic; 3. goat(fauns)

    def set_eyetype(self, etype):
        """
        """
