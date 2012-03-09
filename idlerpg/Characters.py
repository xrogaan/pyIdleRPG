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
        if email is not None and validateEmail(email) < 1:
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

###

colorChart=[(1,'brown')]

class BodyDict(object):
    def __init__(self, dict=None):
        self.__data = {}
        self.__canon_keys = {}
        if dict is not None:
            self.update(dict)
    def __repr__(self):
        return repr(self.__data)
    def __len__(self):
        return len(self.__data)
    def __getitem__(self, key):
        return self.__data[self.__canon_keys[str(key).lower()]]
    def __setitem__(self, key, value):
        if key in self:
            del(self[key])
        self.__data[key] = value
        self.__canon_keys[str(key).lower()] = key
    def __delitem__(self, key):
        current_key = str(key).lower()
        del(self.__data[self.__canon_keys[current_key]])
        del(self.__canon_keys[current_key])
    def __contains__(self, item):
        return self.has_key(item)
    def clear(self):
        self.__data.clear()
        self.__canon_keys.clear()
    def update(self, dict):
        for k, v in dict.items():
            self.__data[k] = v
    def has_key(self, item):
        return str(item).lower() in self.__canon_keys
    def get(self, key, fail=None):
        return self.__data.get(key, fail)
    def items(self):
        return self.__data.items()
    def values(self):
        return self.__data.values()
    def keys(self):
        return self.__data.keys()
    def copy(self):
        import copy
        return copy.copy(self)

class BodyPart(BodyDict):
    def __init__(self, cSize=0, cQuantity=0, cType=0, cColor=None, cRow=None):
        super(BodyPart, self).__init__()
        if cSize>0:
            self.size = cSize
        if cType>0:
            self.type = cType
        if cQuantity>0:
            self.quantity = cQuantity
        if cColor is not None:
            self.color = cColor
        if cRow is not None:
            self.rowId = cRow

    def desc(self):
        return "No description for BodyPart %s" % self.__class__

    def mutate(self, **parts):
        keys = sorted(parts.keys())
        for kw in keys:
            if self.has_key(kw):
                self[kw] = parts[kw]

class Breasts(BodyPart):
    __chart = [((10,12),'AA'),
               ((12,14),'A'),
               ((14,16),'B'),
               ((16,18),'C'),
               ((18,20),'D'),
               ((20,22),'E'),
               ((22,24),'F'),
               ((24,26),'G'),
               ((26,28),'H')]

    def __init__(self, size, rowId):
        super(Breasts, self).__init__(cSize=size, cRow=rowId)

    def __setitem__(self, key, item):
        if key is 'size':
            if not isinstance(item, float):
                raise TypeError("size must be a float")
            self.sizeStr = self.convert2str(size)
        super(Breasts, self).__setitem__(key, item)

    def __delitem__(self, item):
        if item == "size":
            super(Breasts, self).__delitem__('sizeStr')
            return
        if item == "sizeStr":
            return
        super(Breasts, self).__delitem__(item)

    def get_strSize(self, sizeFloat=0):
        if sizeFloat=0:
            return self.sizeStr
        return self.convert2str(sizeFloat)

    def convert2str(self, size):
        if size == int(size):
            raise ValueError('size must be different than %.1f' % size)
        for sizes, name in self._chart:
            if size > sizes[0] and size < sizes[1]:
                return name
        raise ValueError("Couldn't find the right type for %.1f" % size)


class Eyes(BodyPart):
    def __init__(self, etype, ecolor, eqtt):
        super(Eyes, self).__init__(cType=etype, cQuantity=eqtt,
                                   cColor=ecolor)

    def mutate_type(self, newtype):
        self['type'] = newtype

    def mutate_color(self, newcolor):
        self['color'] = newcolor

    def pop(self):
        """
        Won't do what you think it would do.
        """
        self['quantity']-=1

    def extend(self, qtt=1):
        """
        Won't do what you think it would do.
        """
        self['quantity']+=qtt


class Horns(BodyPart):
    def __init__(self, hSize, hType=0, hQtt=0, rowId=None):
        super(Horns,self).__init__(cType=hType, cSize=hSize,
                                      cQuantity=hQtt,cRow=rowId)

class Antennae(Horns):
    pass

class Hairs(BodyPart):
    def __init__(self, size, color):
        """
        size == lenght
        """
        super(Hairs,self).__init__(cSize=size,cColor=color)

class Ears(BodyPart):
    def __init__(self, size, eType):
        """
        size: 1=normal, 2=medium, 3=big
        type: 1=human, 2=pointy
        """
        super(Ears, self).__init__(cSize=size, cType=eType)

class Wings(BodyPart):
    def __init__(self, wSize, wType):
        super(Wings, self).__init__(cSize=wSize, cType=wType)

class Arms(BodyPart):
    def __init__(self, aType):
        super(Arms, self).__init__(cType=aType)

class Legs(BodyPart):
    def __init__(self, lType):
        super(Legs, self).__init__(cType=lType)

class Tail(BodyPart):
    def __init__(self, tType, tSize):
        super(Tail, self).__init__(cType=tType, cSize=tSize)

class Hips(BodyPart):
    def __init__(self, hType):
        super(Hips, self).__init__(cType=hType)

class Anatomy(object):
    def __init__(self):
        self.bodyTypes = ['human', 'demon', 'fauns']
        self.bodyType = 'human'
        self.morphTo = None # changed if a mutator is drank or eaten
        self.face_type = 1 # must be computed out of head type body part.
        self.breasts = []
        self.breasts.append(Breasts(size=10,rowId=len(self.breasts)+1))
        self.ears = Ears(size=1,etype=1)
        self.hairs = Hairs(size=1,color=1)
        self.wings = Wings(wSize=0,wType=0)
        self.eyes = Eyes(etype=1,eqtt=2,ecolor=1)
        self.horns = Horns(hSize=0)
        self.arms = Arms()
        self.legs = Legs()
        self.tail = Tail()
        self.hips = Hips()

