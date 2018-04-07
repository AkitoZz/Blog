import orm 
import asyncio
from model import User,Blog,Comment

def test(loop):
    yield from orm.create_pool(loop,user='mikazuki',password='guo1996127',db='blog')
    u = User(name='Test',email='test@test.com',passwd='123',image='about:blank')
    yield from u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()

    
