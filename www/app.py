import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os,json,time
from datetime import datetime
from aiohttp import web

#from  aiohttp import web

async def index(request):
    return web.Response(body=b'<h1>Awesome</h1>',headers={'content-type':'text/html'})

async def hello(request):
    text = '<h1>Hello,%s</h1>' % request.match_info['name']
    
    
    return web.Response(body=text.encode('utf-8'),content_type='text/html')

#@asyncio.coroutine
async def init(loop):
    app = web.Application()
    app.router.add_get('/',index)
    app.router.add_get('/hello/{name}',hello)
#    srv = await loop.create_server(app.make_handler(),'127.0.0.1',9000)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner,'127.0.0.1',9000)
    await site.start()
#    web.run_app(app,host='127.0.0.1',port=9000)
    logging.info('server started at http://127.0.0.1:9000...')
#    return srv
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
