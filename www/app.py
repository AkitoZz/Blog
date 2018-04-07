#!/usr/bin/env python3

import logging;logging.basicConfig(level=logging.INFO)
import orm
from config import configs
from datetime import datetime
from jinja2 import Environment,FileSystemLoader
from coroweb import add_route,add_routes,add_static
import asyncio,os,json,time
from datetime import datetime
from handlers import cookie2user,COOKIE_NAME 
from aiohttp import web

def init_jinja2(app,**kw):
	logging.info('init jinja2...')

	options = dict(
			autoescape = kw.get('autoescape',True),
			block_start_string = kw.get('block_start_string','{%'),
			block_end_string = kw.get('block_end_string','%}'),
			variable_start_string = kw.get('variable_start_string','{{'),
			variable_end_string = kw.get('variable_end_string','}}'),
			auto_reload = kw.get('auto_reload',True)
			)

	path = kw.get('path',None)
	if not path:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
	env = Environment(loader = FileSystemLoader(path),**options)
	filters = kw.get('filters',None)
	if filters:
		for name,f in filters.items():
			env.filters[name] = f
	app['__template__'] = env

def datetime_filter(t):
	delta = int(time.time() -t)
	if delta < 60:
		return u'1分钟前'
	if delta < 3600:
		return u'%s分钟前' % (delta//60)
	if delta < 86400:
		return u'%s小时前' % (delta//3600)
	if delta < 604800:
		return u'%s天前' % (delta//86400)
	dt = datetime.fromtimestamp(t)
	return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


async def logger_factory(app,handler):
#		@asyncio.coroutine
	async def logeer(request):
		logging.info('Request: %s %s' % (request.method, request.path))	
		#	res = yield from handler(request)
		#	return res            #此处有问题
		#	return (yield from handler(request))
		return await handler(request)
	return logeer

@asyncio.coroutine
def response_factory(app,handler):
	@asyncio.coroutine
	def response(request):
		logging.info('Response handler...')
		r = yield from handler(request)
		logging.info('response result = %s' % str(r))
		if isinstance(r,web.StreamResponse):
			return r
		if isinstance(r,bytes):
			logging.info('*'*10)
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-stream'	
			return resp
		if isinstance(r,str):
			if r.startswith('redirect:'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))	
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r,dict):
			template = r.get('__template__',None)
			if template is None:
				resp = web.Response(body=json.dumps(r,ensure_ascii=False,default=lambda obj:obj.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp		
			else:
				r['__user__'] = request.__user__
				resp = web.Response(body=app['__template__'].get_template(template).render(**r))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r,int) and (600>r>=100):
			resp = web.Response(status=r)
			return resp
		if isinstance(r,tuple) and len(r) == 2:
			status_code,message = r
			if isinstance(status_code,int) and (600>status_code>=100):
				resp = web.Response(status=r,text=str(message))		
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response	

@asyncio.coroutine
def auth_factory(app,handler):
	@asyncio.coroutine
	def auth(request):
		logging.info('check user: %s %s' % (request.method,request.path))
		request.__user__ = None
		cookie_str = request.cookies.get(COOKIE_NAME)
		if cookie_str:
			user = yield from cookie2user(cookie_str)
			if user:
				logging.info('set current user: %s' % user.email)
				request.__user__ =user
		if request.path.startswith('/manage') and (request.__user__ is None or not request.__user__.admin):
			return web.HTTPFound('/signin')
		return (yield from handler(request))
	return auth





if __name__ == '__main__':
	@asyncio.coroutine
	def init(loop):
	#	yield from orm.create_pool(loop,**configs['db'])
		yield from orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='mikazuki', password='guo1996127', db='blog')
		app = web.Application(loop=loop,middlewares=[logger_factory,auth_factory,response_factory])	
		init_jinja2(app,filters=dict(datetime=datetime_filter))
		add_routes(app,'handlers')
		add_static(app)
		srv = yield from loop.create_server(app.make_handler(),'localhost',9000)
		logging.info('server started at http://127.0.0.1:9000')
		return srv

	loop = asyncio.get_event_loop()
	loop.run_until_complete(init(loop))
	loop.run_forever()	

"""
def index(request):
	return web.Response(body=b'<h1>Awesome</h1>',content_type='text/html')
	
@asyncio.coroutine
def init(loop):
	app = web.Application(loop=loop)
	app.router.add_route('GET','/',index)
	srv = yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at http://127.0.0.1:9000')
	return srv
	
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()	
"""