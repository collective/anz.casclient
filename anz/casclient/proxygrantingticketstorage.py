
# python
import datetime

# zope
from Persistence import Persistent
from zope.interface import implements
from zope.bforest.periodic import OOBForest
import transaction

from anz.casclient.interfaces import IProxyGrantingTicketStorage

class ProxyGrantingTicketStorage( Persistent ):
    ''' See interfaces.IProxyGrantingTicketStorage. '''
    
    implements( IProxyGrantingTicketStorage )
    
    # pgtIou validate in almost 60 seconds before it is considered expired.
    TIME_OUT = 60
    
    def __init__( self ):
        ''' Creates a proxy granting ticket storage. '''
        self._mapping = OOBForest(
            datetime.timedelta(seconds=int(self.TIME_OUT/10)), count=11 )
    
    def add( self, pgtIou, pgt ):
        ''' See interfaces.IProxyGrantingTicketStorage. '''
        self._mapping[pgtIou] = pgt
        
        # Commit explicity to make sure the pgt has been saved before we tried
        # to get it during service validate. This will be a issue when anz.cas
        # and anz.casclient deploied on the same zope instance.
        #transaction.commit()
    
    def retrieve( self, pgtIou ):
        ''' See interfaces.IProxyGrantingTicketStorage. '''
        return pgtIou in self._mapping.keys() and self._mapping[pgtIou] or None
