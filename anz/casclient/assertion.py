
# python
import datetime

# zope
from zope.interface import implements

from anz.casclient.interfaces import IAssertion

class Assertion( object ):
    ''' See interfaces.IAssertion. '''
    
    implements( IAssertion )
    
    def __init__( self, principal ):
        ''' Creates a new Assrtion with the supplied Principal.
        
        @param principal
        the Principal object to associate with the Assertion.
        
        '''
        self.principal = principal
    
    def getPrincipal( self ):
        ''' The principal for which this assertion is valid.
        
        @return
        the principal.
        
        '''
        return self.principal
