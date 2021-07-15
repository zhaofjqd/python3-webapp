import myorm
from models import User,Blog,Comment
import asyncio

async def test():
    print("0000")
    await myorm.create_pool(loop=loop,user='www-data',password='www-data',database='awesome')
    print("1111")
    u = User(name='Test',email='Test@126.com',passwd='1234567890',image='about:blank')
    print("2222%s %s %s %s"%(u.name,u.email,u.passwd,u.image))
    
    await u.save()



if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.run_forever()
    loop.close()
    

#for  x in test():
    
#    pass
