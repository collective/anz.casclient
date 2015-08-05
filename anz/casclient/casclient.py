
# python
from xml.dom import minidom as minidom
from urllib import quote
from logging import getLogger

# zope
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from Globals import InitializeClass
from OFS.Cache import Cacheable
from zope.interface import implements
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
import transaction

# cmf
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.interfaces.plugins import \
        IExtractionPlugin, IChallengePlugin, IAuthenticationPlugin, \
        ICredentialsResetPlugin, ICredentialsUpdatePlugin

from anz.casclient.interfaces import IAnzCASClient
from anz.casclient.assertion import Assertion
from anz.casclient.principal import Principal
from anz.casclient.proxygrantingticketstorage import ProxyGrantingTicketStorage
from anz.casclient.sessionmappingstorage import SessionMappingStorage
from anz.casclient.validationspecification import Cas10TicketValidator
from anz.casclient.validationspecification import Cas20ServiceTicketValidator
from anz.casclient.validationspecification import Cas20ProxyTicketValidator
from anz.casclient.validationspecification import Cas20SAMLServiceTicketValidator
from anz.casclient.exceptions import BaseException
from anz.casclient.utils import retrieveResponseFromServer

try:
    from Products.CMFPlone.factory import _IMREALLYPLONE4
    PLONE4 = True
except ImportError:
    PLONE4 = False

LOG = getLogger( 'anz.casclient' )

addAnzCASClientForm = PageTemplateFile(
    'www/add_anzcasclient_form.pt', globals() )

def manage_addAnzCASClient( self, id, title=None, REQUEST=None ):
    ''' Add an instance of anz cas client to PAS. '''
    obj = AnzCASClient( id, title )
    self._setObject( obj.getId(), obj )

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(
            '%s/manage_workspace'
            '?manage_tabs_message='
            'AnzCentralAuthService+added.'
            % self.absolute_url()
            )

class AnzCASClient( BasePlugin, Cacheable ):
    ''' Anz CAS client, Implement as a PAS plugin. '''

    implements( IAnzCASClient )

    meta_type = 'Anz CAS Client'

    # Session variable use to save assertion
    CAS_ASSERTION = '__cas_assertion'

    # The start of the CAS server URL
    casServerUrlPrefix = ''

    # An identify of current service.
    # CAS will redirects to here after login.
    # Set this explicitly but not determine it automatically from request makes
    # us get more security assurance.
    # https://wiki.jasig.org/display/CASC/CASFilter
    serviceUrl = ''

    # Whether to store the Assertion in session or not.
    # If sessions are not used, proxy granting ticket will be required for
    # each request. Default set to True.
    useSession = True

    # If set to True, CAS will ask user for credentials again to authenticate,
    # this may be used for high-security applications. Default set to False.
    renew = False

    # If set to True, CAS will not ask the user for credentials. If the
    # user has a pre-existing single sign-on session with CAS, or if a single
    # sign-on session can be established through non-interactive means
    # (i.e. trust authentication), CAS MAY redirect the client to the URL
    # specified by the "service" parameter, appending a valid service ticket.
    # (CAS also MAY interpose an advisory page informing the client that a CAS
    # authentication has taken place.) If the client does not have a single
    # sign-on session with CAS, and a non-interactive authentication cannot be
    # established, CAS MUST redirect the client to the URL specified by the
    # "service" parameter with no "ticket" parameter appended to the URL. If
    # the "service" parameter is not specified and "gateway" is set, the
    # behavior of CAS is undefined. It is RECOMMENDED that in this case, CAS
    # request credentials as if neither parameter was specified.
    # This parameter is not compatible with the "renew" parameter. Behavior
    # is undefined if both are set to True.
    # See details here: http://www.jasig.org/cas/client-integration/gateway
    gateway = False

    # Use which CAS protocol to validate ticket
    # one of ['CAS 1.0','CAS 2.0']
    ticketValidationSpecification = 'CAS 1.0'
    ticketValidationSpecification_values = ['CAS 1.0','CAS 2.0']

    # The start of the proxy callback url.
    # You should set it point to an instance of this class with protocol 'https'.
    # The result url will be '{proxyCallbackUrlPrefix}/proxyCallback'.
    # If set, means this service will be used as a proxier to access
    # back-end service on behalf of a particular user.
    proxyCallbackUrlPrefix = ''

    # If you provide either the acceptAnyProxy or the allowedProxyChains
    # parameters, a Cas20ProxyTicketValidator will be constructed. Otherwise
    # a Cas20ServiceTicketValidator will be constructed that does not accept
    # proxy tickets.

    # Whether any proxy is OK
    acceptAnyProxy = False

    # Allowed proxy chains.
    # Each acceptable proxy chain should include a space-separated list of URLs.
    # These URLs are proxier's proxyCallbackUrl.
    allowedProxyChains = []

    # Use SAML validation for service ticket validation on CAS 2.0 flow.
    SAMLValidate = False

    security = ClassSecurityInfo()

    _properties = (
        {
            'id': 'serviceUrl',
            'lable': 'Service URL',
            'type': 'string',
            'mode': 'w'
            },
        {
            'id': 'casServerUrlPrefix',
            'lable': 'CAS Server URL Prefix',
            'type': 'string',
            'mode': 'w'
            },
        {
            'id': 'useSession',
            'lable': 'Use Session',
            'type': 'boolean',
            'mode': 'w'
            },
        {
            'id': 'renew',
            'lable': 'Renew',
            'type': 'boolean',
            'mode': 'w'
            },
        {
            'id': 'gateway',
            'lable': 'Gateway',
            'type': 'boolean',
            'mode': 'w'
            },
        {
            'id': 'ticketValidationSpecification',
            'lable': 'Ticket Validation Specification',
            'select_variable': 'ticketValidationSpecification_values',
            'type': 'selection',
            'mode': 'w'
            },
        {
            'id': 'proxyCallbackUrlPrefix',
            'lable': 'Proxy Callback URL Prefix',
            'type': 'string',
            'mode': 'w'
            },
        {
            'id': 'acceptAnyProxy',
            'lable': 'Accept Any Proxy',
            'type': 'boolean',
            'mode': 'w'
            },
        {
            'id': 'allowedProxyChains',
            'label': 'Allowed Proxy Chains',
            'type': 'lines',
            'mode': 'w'
            },
        {
            'id': 'SAMLValidate',
            'label': 'Validate service ticket with SAML',
            'type': 'boolean',
            'mode': 'w'
            },
        )

    def __init__( self, id, title ):
        self._id = self.id = id
        self.title = title
        self._pgtStorage = ProxyGrantingTicketStorage()
        self._sessionStorage = SessionMappingStorage()

    security.declarePrivate( 'extractCredentials' )
    def extractCredentials( self, request ):
        ''' Extract credentials from session or 'request'. '''
        creds = {}

        # Do logout if logout request found
        logoutRequest = request.form.get( 'logoutRequest', '' )
        if logoutRequest:
            self.logoutCallback()
            return creds

        sdm = getattr( self, 'session_data_manager', None )
        assert sdm is not None, 'No session data manager found!'

        session = sdm.getSessionData( create=0 )
        assertion = self.getAssertion( session )
        if not assertion:
            # Not already authenticated. Is there a ticket in the URL?
            ticket = request.form.get( 'ticket', None )
            if not ticket:
                return None # No CAS authentification

            service = self.getService()
            assertion = self.validateServiceTicket( service, ticket )

            # Save current user's session to be used by 'Single Sign Out'
            if not session:
                session = sdm.getSessionData( create=1 )

            # Get session token as id, it is more reliable
            sessionId = session.getContainerKey()
            self._sessionStorage.addSession( ticket, sessionId )

            # Create a session in the default Plone session factory for username
            # depending on the PLONE version used
            username = assertion.getPrincipal().getId()
            if PLONE4:
                # It's needed to cast username which is an unicode type to an
                # str as plone.session does a direct concatenation of unicode
                # username and other string types that leads to an UnicodeDecode
                # error otherwise. It's needed to address plone.session to do
                # not so. Meanwhile, casting the username assumes that there are
                # non ascii chars in it.
                self.session._setupSession(str(username), request.response)
            else:
                # is PLONE3
                cookie = self.session.source.createIdentifier(username)
                creds['cookie'] = cookie
                creds['source'] = 'plone.session'
                self.session.setupSession(username, request.response)

            # Save assertion into session
            if self.useSession:
                # During ticket validation process, the server with this client
                # installed will be callback several times by CAS, this will
                # makes the session data object we get before stale, so here
                # we get it again.
                session = sdm.getSessionData()
                session.set( self.CAS_ASSERTION, assertion )

        creds['login'] = assertion.getPrincipal().getId()
        return creds

    security.declarePrivate( 'authenticateCredentials' )
    def authenticateCredentials( self, credentials ):
        if credentials['extractor'] != self.getId():
            return None

        login = credentials['login']
        return ( login, login )

    security.declarePrivate( 'challenge' )
    def challenge( self, request, response, **kw ):
        ''' Challenge the user for credentials. '''
        # Remove current credentials.
        session = request.SESSION
        session[self.CAS_ASSERTION] = None

        # Redirect to CAS login URL.
        if self.casServerUrlPrefix:
            url = self.getLoginURL() + '?service=' + self.getService()
            if self.renew:
                url += '&renew=true'
            if self.gateway:
                url += '&gateway=true'

            response.redirect( url, lock=1 )
            return 1

        # Fall through to the standard unauthorized() call.
        return 0

    security.declarePrivate( 'resetCredentials' )
    def resetCredentials( self, request, response ):
        ''' Clears credentials and redirects to CAS logout page. '''
        session = request.SESSION
        session.clear()

        if self.casServerUrlPrefix:
            return response.redirect( self.getLogoutURL(), lock=1 )

    security.declarePublic( 'proxyCallback' )
    def proxyCallback( self, pgtId=None, pgtIou=None ):
        ''' See interfaces.IAnzCASClient. '''
        ret = 'success'
        if pgtId and pgtIou:
            self._pgtStorage.add( pgtIou, pgtId )
            ret = '<?xml version=\"1.0\"?>'
            ret += '<casClient:proxySuccess xmlns:casClient="http://www.yale.edu/tp/casClient" />'

        return ret

    security.declarePublic( 'logoutCallback' )
    def logoutCallback( self ):
        ''' See interfaces.IAnzCASClient. '''
        msg = 'No session id found.'
        dom = minidom.parseString( self.REQUEST.form.get('logoutRequest','') )
        SAMLP_NS = 'urn:oasis:names:tc:SAML:2.0:protocol'
        elements = dom.getElementsByTagNameNS( SAMLP_NS,
                                               'SessionIndex' )
        if elements:
            mappingId = elements[0].firstChild.data
            sessionId = self._sessionStorage.getSessionId( mappingId )
            self._sessionStorage.removeByMappingId( mappingId )

            sdm = getattr( self, 'session_data_manager', None )
            assert sdm is not None, 'No session data manager found!'

            session = sdm.getSessionDataByKey( sessionId )
            if session:
                session.clear()

                # We must commit here to make sure the session will be cleared.
                transaction.commit()

            msg = 'Logout seccess.'

        return msg

    security.declarePublic( 'validateProxyTicket' )
    def validateProxyTicket( self, ticket ):
        ''' See interfaces.IAnzCASClient. '''
        validator = Cas20ProxyTicketValidator(
            self.casServerUrlPrefix,
            self._pgtStorage,
            acceptAnyProxy=self.acceptAnyProxy,
            allowedProxyChains=self.allowedProxyChains,
            renew=self.renew )

        try:
            assertion = validator.validate( ticket, self.getService() )
        except BaseException, e:
            LOG.warning( e )
            return False, None
        except Exception, e:
            LOG.warning( e )
            return False, None
        else:
            return True, assertion

    def getLoginURL( self ):
        ''' See interfaces.IAnzCASClient. '''
        return self.casServerUrlPrefix + '/login'

    def getLogoutURL( self ):
        ''' See interfaces.IAnzCASClient. '''
        return self.casServerUrlPrefix + '/logout?url=%s' % self.getService()

    def getService( self ):
        ''' See interfaces.IAnzCASClient. '''
        serviceUrl = ''

        if self.serviceUrl:
            # use explicitly setted service url
            serviceUrl = self.serviceUrl
        else:
            # extract service URL from REQUEST and remove the ticket parameters.
            request = self.REQUEST

            # get query string but strip ticket parameter
            query_string = request.get( 'QUERY_STRING', '' )
            parts = [ p for p in query_string.split('&') if \
                      (p and p.find( 'ticket=' )!=0) ]

            url = request.get( 'ACTUAL_URL', request['URL'] )

            serviceUrl = '%s?%s' % ( url, '&'.join(parts) )

        return quote( serviceUrl )

    def getProxyCallbackUrl( self ):
        ''' See interfaces.IAnzCASClient. '''
        return self.proxyCallbackUrlPrefix and \
               '%s/proxyCallback' % self.proxyCallbackUrlPrefix or ''

    def getAssertion( self, session ):
        ''' See interfaces.IAnzCASClient. '''
        assertion = None

        if self.useSession and session:
            sessionValue = session.get( self.CAS_ASSERTION )
            if isinstance( sessionValue, Assertion ):
                assertion = sessionValue

        return assertion

    def validateServiceTicket( self, service, ticket ):
        ''' See interfaces.IAnzCASClient. '''
        if self.ticketValidationSpecification == 'CAS 1.0':
            validator = Cas10TicketValidator(
                self.casServerUrlPrefix, self.renew )
        else:
            if self.acceptAnyProxy or self.allowedProxyChains:
                validator = Cas20ProxyTicketValidator(
                    self.casServerUrlPrefix,
                    self._pgtStorage,
                    acceptAnyProxy=self.acceptAnyProxy,
                    allowedProxyChains=self.allowedProxyChains,
                    renew=self.renew )
            else:
                if self.SAMLValidate:
                    validator = Cas20SAMLServiceTicketValidator(
                        self.casServerUrlPrefix, self._pgtStorage, self.renew)
                else:
                    validator = Cas20ServiceTicketValidator(
                        self.casServerUrlPrefix, self._pgtStorage, self.renew )

        return validator.validate(
            ticket, service, self.getProxyCallbackUrl() )

classImplements( AnzCASClient,
                 IExtractionPlugin,
                 IChallengePlugin,
                 ICredentialsResetPlugin,
                 IAuthenticationPlugin )

InitializeClass( AnzCASClient )
