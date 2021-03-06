
__author__ = 'Zhaofengjie'

import aiomysql, logging
from boto.compat import StandardError
from socks import log
logging.basicConfig(level=logging.INFO)

async def  create_pool(loop,**kw):
    logging.info('creat database connection pool ...')
    global __pool
    __pool = await aiomysql.create_pool(
        host = kw.get('host','localhost'),
        port = kw.get('port',3306),
        user = kw['user'],
        password = kw['password'],
        db = kw['database'],
        charset = kw.get('charset','utf8'),
        autocommit = kw.get('autocommit',True),
        maxsize = kw.get('maxsize',10),
        minsize = kw.get('minsize',1),
        loop = loop
        )


async def select(sql,args,size = None):
#    log(sql,args)
    global __pool
    with (await __pool)  as  conn:
        cur = await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace("?","%s"),args or ())
        if size:
            rs = await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()
        await cur.close()
        logging.info('rows returned: %s'%len(re))
        return rs

async def execute(sql, args):
#    log(sql)
    async with __pool.acquire() as conn:
        
        cur = await conn.cursor(aiomysql.DictCursor)
        try:
            
            await cur.execute(sql.replace("?","%s"),args)
            affected = cur.rowcount
            await cur.close()
        except BaseException as e:
            raise
        return affected
    
def creat_args_string(num):
    L=[]
    for n in range(num):
        L.append('?')  
    return ','.join(L)
    
class Field(object):
    def __init__(self,name,column_type,primary_key,default):
        self.name= name
        self.column_type=column_type
        self.primary_key=primary_key
        self.default= default
    def __str__(self):
        return ('%s,%s:%s'%(self.__class__.__name__,self.column_type,self.name))
class StringField(Field):
    def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(50)'):
        super().__init__(name,ddl,primary_key,default)
class BooleanField(Field):
    def __init__(self,name=None,primary_key=False,default=False):
        super().__init__(name,'boolean',primary_key,default)
class IntergerField(Field):
    def __init__(self,name=None,primary_key=False,default=0):
        super().__init__(name,'int',primary_key,default)
class FloatField(Field):
    def __init__(self,name=None,primary_key=False,default=0.0):
        super().__init__(name,'real',primary_key,default)
class TextField(Field):
    def __init__(self,name=None,primary_key=False,default=None):
        super().__init__(name,'text',primary_key,default)



class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        if name == 'Model':
            return type.__new__(cls,name,bases,attrs)
        tablename = attrs.get('__table__',None) or name
        logging.info('found model:%s(table:%s'%(name,tablename))
        mappings = dict()
        fields = []
        primarykey = None
        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info('found mapping: %s==>%s'%(k,v))
                mappings[k] = v
                if v.primary_key:
                    if primarykey:
                        raise RuntimeError('Duplicate primary key for field:%s' % (k))
                    primarykey = k
                    logging.info('primary_key is==>%s'%k)
                else:
                    fields.append(k)
        if not primarykey:
            raise RuntimeError('primary key not found')
        for k in mappings.keys():
             attrs.pop(k)
        escaped_fields = list(map(lambda f:'`%s`'%f,fields))
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tablename
        attrs['__primary_key__'] = primarykey
        attrs['__fields__'] = fields
        attrs['__select__'] = 'select `%s`,%s from `%s`' %(primarykey,','.join(escaped_fields),tablename)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tablename, ','.join(escaped_fields), primarykey, creat_args_string(len(escaped_fields) + 1))

        attrs['__update__']= 'update `%s` set %s where `%s`=?'%(tablename,', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)),primarykey)
        attrs['__delete__']='delete from `%s` where `%s`=?'%(tablename ,primarykey)

        return type.__new__(cls,name,bases,attrs)

class Model(dict,metaclass=ModelMetaclass):
    def __init__(self,**kw):
        super(Model,self).__init__(**kw)

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'"% (key))

    def __setattr__(self,key,value):
        self[key] = value

    def getValue(self,key):
        return getattr(self,key,None)
    def getValueOrDefault(self,key):
        value = getattr(self,key,None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s:%s'%(key,str(value)))
                setattr(self,key,value)
        return value
    @classmethod
    async def findAll(cls,where=None,args=None,**kw):
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('order by',None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit',None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value%s'%str(limit))
        rs = await select(' '.join(sql),args)
        return [cls(**f) for f in rs]
    @classmethod
    async def findNumber(cls,selectField, where=None, args=None):
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        # sql = ['select %s from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
            rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        # rs[0]?????? ??????:??????????????????{'_num_': 15}
        # rs[0]['_num_']?????? {'_num_': 15}???'_num_'???????????????????????????15
        return rs[0]['_num_']
    @classmethod
    async def find(cls,pk):
        rs = await select('%s where `%s`=?'%(cls.__select__,cls.__primary_key__),[pk],1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])
    
#    async def save(self):
#         args=[]
#         args = list(map(self.getValueOrDefault, self.__fields__))
#        # ?????????????????????getValueOrDefault???????????????????????????
#         args.append(self.getValueOrDefault(self.__primary_key__))
#        # ????????????????????????????????????
#         rows = await execute(self.__insert__, args)
#         if rows == 0:
#             logging.warn('failed to update by primary key: affected rows: %s' % rows)
#         else:
#             logging.info('succeed to update by primary key: affected rows: %s' % rows)
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        print("3333args=%s"%(args,))
        print("4444%s"%self.__insert__)
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('Failed to insert record: affected rows: %s' % rows)




    async def update(self):
        ' ?????? '
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows == 0:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)
        else:
            logging.info('succeed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        ' ?????? '
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows == 0:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)
        else:
            logging.info('succeed to update by primary key: affected rows: %s' % rows)    
 
    

    







        
    



        
