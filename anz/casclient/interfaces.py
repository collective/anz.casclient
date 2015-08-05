
# zope
from zope.interface import Interface

class IAnzCASClient( Interface ):
    ''' Interface for the CAS client. '''

    def getLoginURL():
        ''' Retrieve where to send people for logging in.

        '''

    def getLogoutURL():
        ''' Retrieve where to send people for logout.

        '''

    def getService():
        ''' Retrieve identify of current service.
        CAS will redirects to here after login. Set this explicitly but not
        determine it automatically from request makes us get more security
        assurance.

        See here:
        https://wiki.jasig.org/display/CASC/CASFilter

        '''

    def getProxyCallbackUrl():
        ''' Return proxy callback url of current service.
        This is not None when current service act as a proxier to access
        the back-end service on behalf of an authenticated user.

        This URL must be HTTPS, and CAS must verify both that the SSL
        certificate is valid and that its name matches that of the service.

        @return
        Proxy callback url, this URL will uniquely and securely identify
        the proxier service that is proxying the client's authentication.

        '''

    def getAssertion( session ):
        ''' Retrieve assertion from session.

        @param session
        session data object to look assertion at it.

        @return
        an assertion object contains authentication information or None.

        '''

    def validateServiceTicket( service, ticket ):
        ''' Validate service ticket.

        @param service
        service url

        @param ticket
        service ticket

        @return
        an assertion object contains authentication information
        if validate success.

        '''

    def proxyCallback( pgtId=None, pgtIou=None ):
        ''' Callback by CAS server to send pgtId and pgtIou.

        If the HTTP GET returns an HTTP status code of 200 (OK), CAS MUST
        respond to the /serviceValidate (or /proxyValidate) request with
        a service response (Section 2.5.2) containing the proxy-granting
        ticket IOU (Section 3.4) within the <cas:proxyGrantingTicket> block.
        If the HTTP GET returns any other status code, excepting HTTP 3xx
        redirects, CAS MUST respond to the /serviceValidate
        (or /proxyValidate) request with a service response that MUST NOT
        contain a <cas:proxyGrantingTicket> block. CAS MAY follow any HTTP
        redirects issued by the pgtUrl. However, the identifying callback
        URL provided upon validation in the <proxy> block MUST be the same
        URL that was initially passed to /serviceValidate (or /proxyValidate)
        as the "pgtUrl" parameter.

        @param pgtId
        proxy granting ticket

        @param pgtIou
        proxy granting ticket Iou

        '''

    def validateProxyTicket( ticket ):
        ''' Called by proxied service(back-end service) to validate
        proxy ticket on CAS server.

        @param ticket
        proxy ticket wait for validation.

        @return
        (True,assertion) if validate success, variable assertion contains
        authentication info.

        (False,None) if validate failure.

        '''

    def logoutCallback( self ):
        ''' Callback by CAS to do 'Single Sign Out'.
        When logout CAS will callback to each of the services that are
        registered with the system and send a POST request with the following:
        <samlp:LogoutRequest ID="[RANDOM ID]" Version="2.0" IssueInstant="[CURRENT DATE/TIME]">
        <saml:NameID>@NOT_USED@</saml:NameID>
        <samlp:SessionIndex>[SESSION IDENTIFIER]</samlp:SessionIndex>
        </samlp:LogoutRequest>

        At this moment the session identifier is the same as the CAS Service
        Ticket. Use the session identifier to map back to a session which should
        be terminated.

        '''

class IProxyGrantingTicketStorage( Interface ):
    ''' Interface for the storage and retrieval of Proxy Granting Ticket.
    '''

    def add( pgtIou, pgt ):
        ''' Add a proxy granting ticket to the backing storage facility.

        @param pgtIou
        used as the key

        @param pgt
        used as the value

        '''

    def retrieve( pgtIou ):
        ''' Retrieve a proxy granting ticket based on the proxy granting
        ticket Iou.

        Note that implementations are not guaranteed to return the same
        result if retrieve is called twice with the same
        proxyGrantingTicketIou.

        @param pgtIou
        used as the key

        @return
        the ProxyGrantingTicket Id or None if it can't be found

        '''

class IPrincipal( Interface ):
    ''' Represents an authenticated user.
    '''

    def getId():
        ''' Returns the unique id for the Principal.

        @return
        the unique id for the Principal

        '''

    def getProxyTicketFor( service ):
        ''' Retrieves a CAS proxy ticket for this specific principal.

        @param service
        the service we wish to proxy this user to.

        @return
        a String representing the proxy ticket.

        '''

class IAssertion( Interface ):
    ''' Represents a response to a validation request.
    '''

    def getPrincipal():
        ''' The principal for which this assertion is valid.

        @return
        the principal.

        '''

class IProxyRetriever( Interface ):
    ''' Interface to abstract the retrieval of a proxy ticket to make the
    implementation a black box to the client.

    '''

    def getProxyTicketIdFor( pgtId, targetService ):
        ''' Retrieves a proxy ticket for a specific targetService.

        @param pgtId
        the Proxy Granting Ticket Id

        @param targetService
        the service we want to proxy.

        @return
        the ProxyTicket Id if Granted, None otherwise.

        '''

class ITicketValidator( Interface ):
    ''' Interface of ticket validator.

    '''

    def getUrlSuffix():
        ''' Retrieve the endpoint of the validation URL.
        Should be relative (i.e. not start with a "/").
        I.e. validate or serviceValidate.

        @return the endpoint of the validation URL.

        '''

    def validate( ticket, service, proxyCallbackUrl='' ):
        ''' Attempts to validate a ticket for the provided service.

        @param ticket
        the ticket to attempt to validate.

        @param service
        the service this ticket is valid for.

        @param proxyCallbackUrl
        proxy callback url, used in proxy authentication.

        @return an assertion from the ticket.

        '''

    def retrieveResponseFromServer( validationUrl, ticket ):
        ''' Contacts the CAS Server to retrieve the response for the ticket
        validation.

        @param validationUrl
        the url to send the validation request to.

        @param ticket
        the ticket to validate.

        @return
        the response from the CAS server.

        '''

    def parseResponseFromServer( response ):
        ''' Parses the response from the server into a CAS Assertion.

        @param response
        the response from the server, in any format.

        @return
        the CAS assertion if one could be parsed from the response.

        '''

class ISessionMappingStorage( Interface ):
    ''' Stores the mapping between session id and mapping id(service ticket).

    '''

    def getSessionId( mappingId ):
        ''' Retrieve session id by mapping id.

        @param mappingId
        the mapping id or None.

        '''

    def removeByMappingId( mappingId ):
        ''' Remove a session by mapping id.

        @param mappingId
        the mapping id.

        '''

    def removeBySessionId( sessionId ):
        ''' Remove a session by session id.

        @param sessionId
        the id of the session.

        '''

    def addSession( mappingId, sessionId ):
        ''' Add a session to storage.

        @param mappingId
        the mapping id.

        @param sessionId
        the id of the session.

        '''


class ISAMLPropertiesExist(Interface):
    """ Event to be triggered in case the ticket validation type is SAML-based
        and there are existing user properties in the response. A subscriber
        could be configured against it to receive these properties and process
        them as required.
    """
