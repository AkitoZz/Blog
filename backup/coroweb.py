import functools,logging,inspect,asyncio,os
from aiohttp import web
from urllib import parse
logging.basicConfig(level=logging.INFO)

def get(path):
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator
'''
def Handler_decorator(path,*,method):
    def decorator(func):
        @functools.wraps(func)
        def warpper(*args,**kw):
            return func(*args,**kw)
        warpper.__route__ = path
        warpper.__mothod__ = method
        return warpper
    return decorator

get = functools.partial(Handler_decorator,method = 'GET')
post = functools.partial(Handler_decorator,method = 'POST')
'''
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)      

def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name,param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (
            param.kind != inspect.Parameter.VAR_POSITIONAL and
            param.kind != inspect.Parameter.KEYWORD_ONLY and 
            param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request paramter must be the last named parameter in function:%s%s' % (fn.__name__, str(sig)))
    return found

class RequestHandler(object):
    def __init__(self,app,fn):
        self._app = app
        self._func = fn
        self._required_kw_args = get_required_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._has_request_arg = has_request_arg(fn)
        self._has_named_kw_arg = has_named_kw_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)

    @asyncio.coroutine
    def __call__(self,request):
        kw = None
        if self._has_named_kw_arg or self._has_var_kw_arg or self._required_kw_args:
            if request.method == 'POST':
                if request.content_type == None:
                    return web.HTTPBadRequest(text='Missing Content_type.')    
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = yield from request.json()
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest(text='JSON body must be object')    
                    kw = params
                elif ct.startswith('application/x-www-from-urlencoded') or ct.startswith('multipart/from-data'):
                    params = yield from request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)            
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict() 
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k] = v[0]

        if kw is None:
            kw = dict(**request.match_info)
        else:
            if self._has_named_kw_arg and (not self._has_var_kw_arg):
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy                               
            for k,v in request.match_info.items():
                if k in kw:
                    logging.warn('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v    
        if self._has_request_arg:
            kw['request'] = request
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                   # return web.HTTPBadRequest('Missing argument: %s' % name)    
                    #return web.HTTPBadRequest('Missing argument: %s' % name)
                    return web.HTTPBadRequest()

        logging.info('call with args: %s' % str(kw))
        try:
            r = yield from self._func(**kw)
            return r
#        except APIError as e:
#            return dict(error=e.error,data=e.data,message=e.message)
        except:
            return 

def add_route(app,fn):
    method = getattr(fn,'__method__',None)
    path = getattr(fn,'__route__',None)
    if method is None or path is None:
        raise ValueError('@get or @post noet defined in %s ' % fn.__name__)
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method,path,fn.__name__,','.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method,path,RequestHandler(app,fn))

def add_routes(app,module_name):
    n = module_name.rfind('.')
    if n == -1:
        mod = __import__(module_name,globals(),locals,[],0)
    else:
        name = module_name[(n+1):]
        mod = getattr(__import__(module_name[:n],globals(),locals,[name],0),name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod,attr)
        if callable(fn):
            method = getattr(fn,'__method__',None)
            path = getattr(fn,'__route__',None)
            if method and path:
                add_route(app,fn)

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    app.router.add_static('/static/',path)
    logging.info('add static %s => %s ' % ('/static/',path))


















