# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:

import logging

logger = logging.get_logger('character')

item_types = ('consumable', 'armor', 'weapon', 'scroll', 'ring', 'misc')

##
# Database schema:
#  Each document is an item, only one item by user. Therefor, the maximum
#  number of item in game is Iventory_size * Bag
# --
# Keys:
#  character_name, name, type, properties, quantity
##
class Bag(object):
    def __init__(self, characterObj, inventoryObj, collectionObj):
        self._len = 0
        self._bag = dict()
        self._characterObj = characterObj
        self._inventoryObj = inventoryObj
        self._collectionObj = collectionObj
        self._logger = logging.get_logger('Inventory.Bag')
        character_name = self._characterObj.get_characterName()
        bag = self._collectionObj.find({'character': character_name})
        if not bag:
            bag = list()
        for item in bag:
            itemObj = Item(item['name'], item['type'], item['properties'], item['_id'))
            if self._bag.has_key(item['name']):
                logger.warning('Duplicate object %s for user %s',
                                (item['name'], character_name))
            else:
                self._bag.update({item['name']: {
                                    'obj': itemObj,
                                    'quantity': item['quantity']}})
            self._len+=1

    def __len__(self):
        return self._len

    def __getitem__(self, name):
        if self._bag.has_key(name):
            return self._bag[name]
        return None

    def has_key(self, key):
        return self._bag.has_key(key)

    def add_item(self, name, quantity=None):
        if not self._inventoryObj.has_item(name):
            logger.warning('Bag is trying to get an unexistant item `%s\'', name)
            return

        if self._bag.has_key(name):
            if not isinstance(quantity, int):
                quantity = 1
            self._bag[name]['quantity'] += quantity
            self._collectionObj.update({'_id':self._bag[name]['_id']},
                                       {'$inc': {'quantity': 1}})
        else:
            character_name = self._characterObj.get_characterName()
            dbItemProperties = self.inventoryObj.get_item_by_name(name).copy()
            dbItemProperties.pop('dbuid')
            bagItemProperties = dbItemProperties
            dbItemProperties.update({'character_name': character_name,
                                    'quantity': 1})
            _id = self._collectionObj.save(dbIttemProperties, manipulate=True)
            bagItemProperties.update({'_id': _id})
            self._bag.save({name: {'obj': Item(**bagItemProperties),
                                   'quantity': 1}})
        self._len+=1

    def remove_item(self, name):
        if not self._inventoryObj.has_item(name):
            logger.warning('Cannot remove item %s: unexistant.', name)

        if not self._bag.has_key(name):
            return -1

        if self._bag[name]['quantity'] > 1:
            self._bag[name]['quantity'] -= 1
            self._collectionObj.update({'_id': self.bag[name]['obj'].dbuid},
                                       {'$inc': {'quantity': -1}})
        else:
            self._collectionObj.remove({'_id': self._bag[name]['obj'].dbuid})
            del self._bag[name]
        self._len-=1


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
        self._logger = logging.get_logger('Inventory.Inventory')

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

        self._logger.warning('Trying to get an unexistant item by name `%s\'',
                             name)
        return -1

    def get_items_by_type(self, itype):
        if type not in item_types or not self._itypes.has_key(itype):
            self._logger.warning('Trying to get an item by a unexistant '\
                                 'type %s', itype)
            return -1
        return self._itypes[type]


class Item(object):
    def __init__(self, name, itype, properties, dbuid=None):
        self.name = name
        self.type = itype
        self.properties = properties
        self._logger = logging.get_logger('Inventory.Item')
        if dbuid:
            self.dbuid = dbuid

    def copy(self):
        return {'name': self.name, 'type': self.type,
                'properties': self.properties, '_id': self.dbuid}

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value not in item_types:
            self._logger.warning('Unknown item(%s) type %s',
                                 (self._type, self._name))
        self._type = value

    @type.deleter
    def type(self):
        del self._type

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, value):
        if not isinstance(value, dict):
            self._logger.critical('Properties type mismatch. Got %s expected '\
                                  'dict for item %s', (type(value), self.name))
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

