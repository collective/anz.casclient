
# python
import socket
from urllib2 import urlopen, URLError, HTTPError
from logging import getLogger

from anz.casclient.exceptions import ConnectionException

LOG = getLogger( 'anz.casclient' )

def retrieveResponseFromServer( url ):
    ''' Contacts the CAS Server and retrieve the response.
    '''
    socket.setdefaulttimeout( 5 )
    try:
        response = urlopen( url )
    except HTTPError, e:
        LOG.warning( e )
        raise ConnectionException( 'Error code: %s' % e.code )
    except URLError, e:
        LOG.warning( e )
        raise ConnectionException( 'Fail to connect, %s' % e.reason )
    except Exception, e:
        LOG.warning( e )
        raise
    
    return response.read()
