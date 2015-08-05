from zope.interface import implements
from anz.casclient.interfaces import ISAMLPropertiesExist


class SAMLPropertiesExist(object):
    implements(ISAMLPropertiesExist)

    def __init__(self, properties):
        self.properties = properties
