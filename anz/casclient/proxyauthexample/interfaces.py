
# zope
from zope.interface import Interface

class IProxyAuthExampleView( Interface ):
    ''' Interface for the proxy authentication example view. '''
    
    def getUserInfo( ticket ):
        ''' Running on back-end service to return id of the user whom the
        ticket authenticates.
        
        @param ticket
        proxy ticket.
        
        @return
        string message represent running status.
        
        '''
    
    def getUserInfoFromTargetService():
        ''' Running on proxier service to ask back-end service for user info.
        '''
