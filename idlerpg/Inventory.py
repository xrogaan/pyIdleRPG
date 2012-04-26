# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:

import logging

logger = logging.get_logger('character')

item_types = ('consumable', 'armor', 'weapon', 'scroll', 'ring', 'misc')

class Bag(object):
    def __init__(self, characterObj, inventoryObj, collectionObj):
        self._len = 0
        self._bag = dict()
        self._characterObj = characterObj
        self._inventoryObj = inventoryObj
        self._collectionObj = collectionObj
        character_name = self._characterObj.get_characterName()
        bag = self._collectionObj.find({'character': character_name})
        if not bag:
            bag = list()
        for item in bag:
            itemObj = Item(item['name'], item['type'], item['properties'], item['_id'))
            if self._bag.has_key(item['name']):
                self._bag[item['name']][1]+=1
            else:
                self._bag.update(item['name']: (itemObj, 1))
            self._len+=1

    def __len__(self):
        return self._len

    def __getitem__(self, name):
        if self._bag.has_key(name):
            return self._bag[name]
        return None

    def has_key(self, key):
        return self._bag.has_key(key)

##
# dbkey: unique key to link character sheet to its inventory
# dblink: link to the mongo Connection object
##
class Inventory:
    def __init__(self, dbkey, dblink):
        self.dbItems = dblink['items']
        # type indexed item dict
        self._itypes = dict()
        # name indexed item dict
        self._inames = dict()
        # unindexed item list
        self._items = list()

    def fetch_all(self):
        for itype in item_types:
            t = self.dbItems.find({'type': itype})
            itemObj = Item(t['name'], t['type'], t['properties'])
            del(t)
            if not self._itypes.has_key(itype):
                self._itypes.update({itype: list()})
            self._itypes[itype].append(itemObj)
            self._inames.update({itemObj.name: itemObj})
            self._items.append(itemObj)

    def remove_item(self, name):
        if name not in self._inames.keys():
            return -1

        itype = self._inames[name]
        del self._inames[name],self._itypes[itype]
        for item in self._items:
            if item.name == name:
                index = self._items.index(item)
                break
        del self._items[index], item

    def has_item(self, name):
        return self._iname.has_key(name)

    def get_item_by_name(self, name):
        if name in self._inames.keys():
            return self._inames[name]

        logger.warning('Trying to get an unexistant item by name `%s\'', name)
        return -1

    def get_items_by_type(self, type):
        if type not in item_types or not self._itypes.has_key(type):
            logger.warning('Trying to get an item by a unexistant type %s', type)
            return -1
        return self._itypes[type]


class Item(object):
    def __init__(self, name, itype, properties, dbuid=None):
        self.name = name
        self.type = itype
        self.properties = properties
        if dbuid:
            self.dbuid = dbuid

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value not in item_types:
            d = {'name': self._name, 'properties': self._properties}
            logger.warning('Unknown item type %s', self._type, extra=d)
        self._type = value

    @type.deleter
    def type(self):
        del self._type

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, value):
        if type(value) != type(dict()):
            logger.critical('Properties type mismatch. Got %s expected dict.',
                            type(value),extra={'name':self.name})
            self._properties = None
            return
        self._properties = value

    @properties.deleter
    def properties(self):
        del self._properties

    def getProperty(self, name=None):
        if name is not None:
            return self.properties.get(name, -1)
        return self.properties

