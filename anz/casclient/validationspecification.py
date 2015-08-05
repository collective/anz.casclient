
# python
from xml.dom import minidom as minidom
from datetime import datetime
from xml.etree import ElementTree

# zope
from zope.interface import implements
from zope.event import notify
import transaction

from anz.casclient.interfaces import ITicketValidator
from anz.casclient.events import SAMLPropertiesExist
from anz.casclient.principal import Principal
from anz.casclient.assertion import Assertion
from anz.casclient.proxyretriever import Cas20ProxyRetriever
from anz.casclient.utils import retrieveResponseFromServer
from anz.casclient.exceptions import TicketValidationException, \
     InternalException, ConnectionException, InvalidProxyChainException

import requests
import time


class TicketValidator( object ):
    ''' Validator that will confirm the validity of a supplied ticket.
    '''

    implements( ITicketValidator )

    def __init__( self, casServerUrlPrefix, renew=False ):
        ''' Construct a ticket validator object. '''
        self.casServerUrlPrefix = casServerUrlPrefix
        self.renew = renew

    def getUrlSuffix( self ):
        ''' See interfaces.ITicketValidator. '''
        raise NotImplementedError

    def validate( self, ticket, service, proxyCallbackUrl='' ):
        ''' See interfaces.ITicketValidator. '''
        validationUrl = self._constructValidationUrl(
            ticket, service, proxyCallbackUrl )
        serverResponse = self.retrieveResponseFromServer(
            validationUrl, ticket )

        if not serverResponse:
            raise 'The CAS server returned no response.'

        return self.parseResponseFromServer( serverResponse )

    def retrieveResponseFromServer( self, validationUrl, ticket ):
        ''' See interfaces.ITicketValidator. '''
        return retrieveResponseFromServer( validationUrl )

    def parseResponseFromServer( self, response ):
        ''' See interfaces.ITicketValidator. '''
        raise NotImplementedError

    def _constructValidationUrl( self, ticket, service, proxyCallbackUrl ):
        ''' Constructs the URL to send the validation request to.

        @param ticket
        the ticket to be validated.

        @param service
        the service identifier.

        @param proxyCallbackUrl
        proxy callback url, used in proxy authentication.

        @return
        the fully constructed URL.

        '''
        url = []
        url.append( self.casServerUrlPrefix )
        if not self.casServerUrlPrefix[-1] == '/':
            url.append( '/' )

        url.append( self.getUrlSuffix() )
        url.append( '?' )

        url.append( 'ticket=%s' % ticket )
        url.append( '&service=%s' % service )

        if self.renew:
            url.append( '&renew=true' )

        if proxyCallbackUrl:
            url.append( '&pgtUrl=%s' % proxyCallbackUrl )

        return ''.join( url )

class Cas10TicketValidator( TicketValidator ):
    ''' Implementation of a Ticket Validator that can validate tickets
    conforming to the CAS 1.0 specification.

    '''
    def getUrlSuffix( self ):
        ''' See interfaces.ITicketValidator. '''
        return 'validate'

    def parseResponseFromServer( self, response ):
        ''' See interfaces.ITicketValidator. '''
        lines = response.split( '\n' )
        first = lines[0]
        if not first=='yes':
            raise 'CAS Server could not validate ticket.'

        userId = lines[1]
        return Assertion( Principal( userId ) )

class Cas20ServiceTicketValidator( TicketValidator ):
    ''' Implementation of the Ticket Validator that will validate Service
    Tickets in compliance with the CAS 2.

    '''
    CAS_NS = 'http://www.yale.edu/tp/cas'

    def __init__( self, casServerUrlPrefix, pgtStorage, renew=False ):
        super(Cas20ServiceTicketValidator, self).__init__( casServerUrlPrefix,
                                                           renew )
        self.pgtStorage = pgtStorage

    def getUrlSuffix( self ):
        ''' See interfaces.ITicketValidator. '''
        return 'serviceValidate'

    def parseResponseFromServer( self, response ):
        ''' See interfaces.ITicketValidator. '''
        try:
            dom = minidom.parseString( response )
            elements = dom.getElementsByTagNameNS( self.CAS_NS,
                                                   'authenticationFailure' )
            if elements:
                raise TicketValidationException( elements[0].firstChild.data )

            elements = dom.getElementsByTagNameNS( self.CAS_NS, 'user' )
            userId = elements and elements[0].firstChild.data or None
            if not userId:
                raise TicketValidationException(
                    'No principal was found in the response.' )

            elements = dom.getElementsByTagNameNS( self.CAS_NS,
                                                   'proxyGrantingTicket' )
            pgtIouNode = elements and elements[0] or None
            if pgtIouNode:
                pgtIou = pgtIouNode.firstChild.data

                # Explicite call transaction.begin() to sync invalidations
                # for a given transaction, make sure to get the latest pgt
                # storage data. This will be a issue when anz.cas and
                # anz.casclient deploied on the same zope instance.
                transaction.begin()

                pgt = self.pgtStorage.retrieve( pgtIou )
                if pgt:
                    principal = Principal(
                        userId, pgt,
                        Cas20ProxyRetriever(self.casServerUrlPrefix) )
                else:
                    raise TicketValidationException(
                        'No pgt found for pgtIou %s.' % pgtIou )
            else:
                principal = Principal( userId )

            return Assertion( principal )
        except Exception, e:
            raise InternalException( str(e) )

class Cas20ProxyTicketValidator( Cas20ServiceTicketValidator ):
    ''' Extension Service Ticket validation to validate service tickets and
    proxy tickets.

    '''
    def __init__( self, casServerUrlPrefix, pgtStorage, acceptAnyProxy=True,
                  allowedProxyChains=[], renew=False ):
        super(Cas20ProxyTicketValidator, self).__init__( casServerUrlPrefix,
                                                         pgtStorage,
                                                         renew )

        self.acceptAnyProxy = acceptAnyProxy
        self.allowedProxyChains = allowedProxyChains

    def getUrlSuffix( self ):
        ''' See interfaces.ITicketValidator. '''
        return 'proxyValidate'

    def parseResponseFromServer( self, response ):
        ''' See interfaces.ITicketValidator. '''
        assertion = super(Cas20ProxyTicketValidator, self).\
                  parseResponseFromServer( response )

        self._validateProxyChain( response )

        return assertion

    def _validateProxyChain( self, response ):
        dom = minidom.parseString( response )
        elements = dom.getElementsByTagNameNS( self.CAS_NS,
                                               'proxy' )
        proxies = []
        for e in elements:
            proxies.append( e.firstChild.data )
        proxies = ' '.join( proxies )

        if self.acceptAnyProxy or not proxies or \
           proxies in self.allowedProxyChains:
            return True

        raise InvalidProxyChainException( 'Invalid proxy chain: %s' % proxies )


class Cas20SAMLServiceTicketValidator(TicketValidator):
    ''' Implementation of the Ticket Validator that will validate Service
    Tickets in compliance with the CAS 2 using the SAML validation to enable
    extraction of custom user attributes.
    '''
    SAML_NS = '{urn:oasis:names:tc:SAML:1.0:assertion}'

    def __init__(self, casServerUrlPrefix, pgtStorage, renew=False):
        super(Cas20SAMLServiceTicketValidator, self).__init__(casServerUrlPrefix,
                                                           renew)
        self.pgtStorage = pgtStorage

    def getUrlSuffix(self):
        ''' See interfaces.ITicketValidator. '''
        return 'samlValidate'

    def parseResponseFromServer(self, response):
        ''' See interfaces.ITicketValidator. '''
        try:
            tree = ElementTree.fromstring(response)
            status_code_tag = tree.findall('.//{urn:oasis:names:tc:SAML:1.0:protocol}StatusCode')

            if status_code_tag:
                status_code = status_code_tag[0].attrib['Value']
                if status_code != 'saml1p:Success':
                    raise TicketValidationException(status_code)
            else:
                raise TicketValidationException(
                    'No principal was found in the response.')

            username_tag = tree.findall('.//{}NameIdentifier'.format(self.SAML_NS))
            if username_tag:
                username = username_tag[0].text
            else:
                raise TicketValidationException(
                    'No principal was found in the response.')

            principal = Principal(username)

            attribute_tag = tree.findall('.//{}Attribute'.format(self.SAML_NS))

            if attribute_tag:
                properties = {}
                for attribute in attribute_tag:
                    attribute_key = attribute.attrib['AttributeName']
                    value_tag = attribute.getchildren()
                    if value_tag:
                        attribute_value = value_tag[0].text

                    properties.update({attribute_key: attribute_value})
                properties.update(dict(username=username))
                notify(SAMLPropertiesExist(properties))

            return Assertion(principal)
        except Exception, e:
            raise InternalException(str(e))

    def retrieveResponseFromServer(self, validationUrl, ticket):
        ''' See interfaces.ITicketValidator. '''

        request_id = '_192.168.16.51.' + str(int(time.time()))
        request_instant = datetime.isoformat(datetime.now()) + 'Z'
        payload = """<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body><samlp:Request xmlns:samlp="urn:oasis:names:tc:SAML:1.0:protocol" MajorVersion="1" MinorVersion="1" RequestID="{request_id}" IssueInstant="{request_instant}"><samlp:AssertionArtifact>{ticket}</samlp:AssertionArtifact></samlp:Request></SOAP-ENV:Body></SOAP-ENV:Envelope>""".format(**dict(request_id=request_id, request_instant=request_instant, ticket=ticket))
        req = requests.post(validationUrl, payload, headers={'Content-Type': 'text/xml'})
        return req.text

    def _constructValidationUrl(self, ticket, service, proxyCallbackUrl):
        ''' Constructs the URL to send the validation request to.

        @param service
        the service identifier.

        @return
        the fully constructed URL.

        '''
        url = []
        url.append(self.casServerUrlPrefix)
        if not self.casServerUrlPrefix[-1] == '/':
            url.append('/')

        url.append(self.getUrlSuffix())
        url.append('?')

        url.append('TARGET=%s' % service)

        return ''.join(url)
