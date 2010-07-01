
# python
from urllib import quote
from xml.dom import minidom as minidom

# zope
from zope.interface import implements

from anz.casclient.interfaces import IProxyRetriever
from anz.casclient.utils import retrieveResponseFromServer

class Cas20ProxyRetriever( object ):
    ''' Implementation of a ProxyRetriever that follows the CAS 2.0.
    In general, this class will make a call to the CAS server with
    some specified parameters and receive an XML response to parse.
    
    '''
    
    implements( IProxyRetriever )
    
    CAS_NS = 'http://www.yale.edu/tp/cas'
    
    def __init__( self, casServerUrl ):
        ''' Construct a proxy retriever object.
        
        @param casServerUrl
        the URL to the CAS server
        
        '''
        self.casServerUrl = casServerUrl
    
    def getProxyTicketIdFor( self, pgtId, targetService ):
        ''' See interfaces.IProxyRetriever. '''
        ret = None
        
        url = self._constructUrl( pgtId, targetService )
        response = retrieveResponseFromServer( url )
        dom = minidom.parseString( response )
        elements = dom.getElementsByTagNameNS( self.CAS_NS,
                                               'proxyFailure' )
        if not elements:
            elements = dom.getElementsByTagNameNS( self.CAS_NS,
                                                   'proxyTicket' )
            ret = elements[0].firstChild.data
        
        return ret
    
    def _constructUrl( self, pgtId, targetService ):
        url = []
        url.append( self.casServerUrl )
        if not self.casServerUrl[-1] == '/':
            url.append( '/' )
        
        url.append( 'proxy?' )
        url.append( 'pgt=%s&' % pgtId )
        url.append( 'targetService=%s' % quote(targetService) )
        
        return ''.join( url )
