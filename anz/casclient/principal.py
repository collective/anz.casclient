
# zope
from zope.interface import implements

from anz.casclient.interfaces import IPrincipal

class Principal( object ):
    ''' See interfaces.IPrincipal. '''
    
    implements( IPrincipal )
    
    def __init__( self, id, pgt=None, proxyRetriever=None ):
        ''' Construct an principal object.
        
        @param id
        the id of principal
        
        @param pgt
        proxy granting ticket id
        
        @param proxyRetriever
        used to retrieve a proxy ticket from a CAS server
        
        '''
        self.id = id
        self.pgt = pgt
        self.proxyRetriever = proxyRetriever
    
    def getId( self ):
        ''' See interfaces.IPrincipal. '''
        return self.id
    
    def getProxyTicketFor( self, service ):
        ''' See interfaces.IPrincipal. '''
        ret = None
        if self.pgt:
            ret = self.proxyRetriever.getProxyTicketIdFor( self.pgt, service )
        
        return ret
