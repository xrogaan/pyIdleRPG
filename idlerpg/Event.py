# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=80:

"""
TODO: créer une anatomie
quest t1:

handofgod:
    text: "%s god blessed by ..."
"""

class Event:
    def __init__(self):
        self.type=None
        self.text=None
        self.opts=[]
        self.odds=None

    def get_odds(self):
        import random
        return random.randint((self.odds*86400)/clock)

    def get_text(self, people=[]i):
        return self.text % tuple(people)

