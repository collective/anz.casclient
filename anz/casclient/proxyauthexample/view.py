
# zope
from Products.Five import BrowserView
from zope.interface import implements

from anz.casclient.utils import retrieveResponseFromServer
from anz.casclient.proxyauthexample.interfaces import IProxyAuthExampleView

class ProxyAuthExampleView( BrowserView ):
    ''' An example view to show how to use proxy authentication. '''
    
    implements( IProxyAuthExampleView )
    
    def __init__( self, context, request ):
        super(ProxyAuthExampleView, self).__init__( context, request )
        
        # eg. http://xx.xx.xx.xx:8080/backend
        #self.BACK_END_SERVICE_URL = '{URL OF YOUR BACK-END SERVICE}'
        self.BACK_END_SERVICE_URL = 'http://cas.server:5150/backend'
        
        # eg. /plone/acl_users/anz_casclient
        #self.PATH_TO_PROXIER_PLUGIN = \
        #    '{PATH TO YOUR PROXIER ANZ.CASCLIENT PLUGIN}'
        self.PATH_TO_PROXIER_PLUGIN = '/plone/acl_users/anz_casclient'
        
        # eg. /backend/acl_users/anz_casclient
        #self.PATH_TO_BACK_END_PLUGIN = \
        #    '{PATH TO YOUR BACK END ANZ.CASCLIENT PLUGIN}'
        self.PATH_TO_BACK_END_PLUGIN = '/backend/acl_users/anz_casclient'
    
    def getUserInfo( self, pt ):
        ''' Running on back-end service to return id of the user whom the
        ticket authenticates.
        
        @param pt
        proxy ticket.
        
        @return
        string message represent running status.
        
        '''
        plugin = self.context.restrictedTraverse(
            self.PATH_TO_BACK_END_PLUGIN, None )
        if plugin:
            success, assertion = plugin.validateProxyTicket( pt )
            
            if success:
                return 'Hello, %s!' % \
                       ( assertion and assertion.getPrincipal().getId() or None )
            else:
                return 'You are not authorized to get user info.'
        
        return 'Get back-end service anz.casclient plugin fail,check your path setting.'
    
    def getUserInfoFromTargetService( self ):
        ''' Running on proxier service to ask back-end service for user info.
        '''
        request = self.request
        context = self.context
        
        # get cas client plugin instance
        plugin = context.restrictedTraverse(
            self.PATH_TO_PROXIER_PLUGIN, None )
        if plugin:
            assertion = plugin.getAssertion( request.SESSION )
            if not assertion:
                return 'No assertion found.'
            else:
                # get proxying ticket
                pt = assertion.getPrincipal().getProxyTicketFor(
                    self.BACK_END_SERVICE_URL )
                
                # call proxied service
                url = '%s/@@proxyAuthExample/getUserInfo?pt=%s' % \
                    ( self.BACK_END_SERVICE_URL, pt )
                response = retrieveResponseFromServer( url )
                return response
        
        return 'Get proxier service anz.casclient plugin fail, check your path setting.'
