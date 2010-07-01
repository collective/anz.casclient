
class BaseException( Exception ):
    ''' Base class for exceptions in this module. '''
    pass

class TicketValidationException( BaseException ):
    ''' Exception to be thrown when ticket validation fails. '''
    ERROR_CODE = 'INVALID_TICKET'

class InternalException( BaseException ):
    ''' '''
    ERROR_CODE = 'INTERNAL_ERROR'
    
class ConnectionException( BaseException ):
    ''' '''
    ERROR_CODE = 'CONNECTION_ERROR'

class InvalidProxyChainException( BaseException ):
    ''' '''
    ERROR_CODE = 'INVALID_PROXY_CHAIN'
