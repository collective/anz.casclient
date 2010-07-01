
# python
from datetime import timedelta

# zope
from Persistence import Persistent
from zope.interface import implements
from zope.bforest.periodic import OOBForest

from anz.casclient.interfaces import ISessionMappingStorage

class SessionMappingStorage( Persistent ):
    ''' See interfaces.ISessionMappingStorage. '''
    
    implements( ISessionMappingStorage )
    
    def __init__( self ):
        ''' Creates a proxy granting ticket storage. '''
        # mapping id as key, session id as value
        self._mapping_id_to_session_id = OOBForest(
            timedelta(hours=1), count=3 )
        
        # session id as key, mapping id as value
        self._session_id_to_mapping_id = OOBForest(
            timedelta(hours=1), count=3 )
    
    def getSessionId( self, mappingId ):
        ''' See interfaces.ISessionMappingStorage. '''
        return mappingId in self._mapping_id_to_session_id.keys() and \
               self._mapping_id_to_session_id[mappingId] or None
    
    def removeByMappingId( self, mappingId ):
        ''' See interfaces.ISessionMappingStorage. '''
        if mappingId in self._mapping_id_to_session_id.keys():
            sessionId = self._mapping_id_to_session_id[mappingId]
            
            del self._session_id_to_mapping_id[sessionId]
            del self._mapping_id_to_session_id[mappingId]
    
    def removeBySessionId( self, sessionId ):
        ''' See interfaces.ISessionMappingStorage. '''
        if sessionId in self._session_id_to_mapping_id.keys():
            mappingId = self._session_id_to_mapping_id[sessionId]
            
            del self._session_id_to_mapping_id[sessionId]
            del self._mapping_id_to_session_id[mappingId]
    
    def addSession( self, mappingId, sessionId ):
        ''' See interfaces.ISessionMappingStorage. '''
        self._mapping_id_to_session_id[mappingId] = sessionId
        self._session_id_to_mapping_id[sessionId] = mappingId
