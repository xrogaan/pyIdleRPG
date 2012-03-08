# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:

class Item:
    _knownTypes = ['armor']
    def __init__(self, name, type, property):
        self.name = name
        self._type = type
        self._property = property

        if self._type not in self._knownTypes:
            raise Exception('Unknown item type '+self._type)

    def getType(self):
        return self._type

    def getPropetry(self, name=None):
        if name is not None:
            return self._property.get(name, -1)
        return self._property

    def __repr__(self):
        return "%s(name=%s, type=%s, property=%s)" % {
            self.__class__.__name__, self._name, self._type, self._property)
