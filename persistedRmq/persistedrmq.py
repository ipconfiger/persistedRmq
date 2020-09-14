# coding=utf8

__author__ = 'Alexander.Li'

import aioredis
import logging
import time


class PersistedRmq(object):
    redis_uri: str
    conn: object
    timestamp: int

    @classmethod
    def init(cls, uri):
        cls.redis_uri = uri

    def __init__(self, channel, client_id=None, on_message=None):
        self.channel = channel
        self.client_id = client_id
        self.on_message = on_message
        self.lock_key = f'{self.channel}-{self.client_id}'
        self.queue_key = f'{self.channel}-{self.client_id}-queue'
        self.subscribe_chn = f'chn:{self.channel}'
        self.persisted_timeout = 3600 * 24 * 3

    async def __aenter__(self):
        await self.init_mq()
        return self

    async def __aexit__(self, *args):
        await self.close()

    def __await__(self):
        return self.__aenter__().__await__()

    async def close(self):
        self.conn.close()
        await self.conn.wait_closed()

    async def connect(self):
        self.conn = await aioredis.create_redis_pool(self.__class__.redis_uri)

    async def init_mq(self):
        await self.connect()
        if self.on_message:
            self.timestamp = int(time.time() * 1000)
            await self.set('client-map', self.lock_key, self.timestamp)

    async def set(self, prefix, key, value):
        await self.conn.set(f'{prefix}:{key}', value, expire=3600 * 24 * 3)

    async def get(self, prefix, key):
        return await self.conn.get(f'{prefix}:{key}')

    async def expire(self, key, timeout):
        return await self.conn.expire(key, timeout)

    async def hash_get(self, client_id=None):
        if client_id:
            return await self.conn.hget(f'fail:{self.channel}', client_id)
        else:
            return await self.conn.hget(f'fail:{self.channel}', self.client_id)

    async def hash_set(self, value):
        return await self.conn.hset(f'fail:{self.channel}', self.client_id, value)

    async def hash_del(self):
        return await self.conn.hdel(f'fail:{self.channel}', self.client_id)

    async def hash_keys(self):
        return await self.conn.hkeys(f'fail:{self.channel}')

    async def duplicate(self) -> bool:
        ts = await self.get('client-map', self.lock_key)
        logging.error(f'duplicate:{ts} vs {self.timestamp}')
        return int(ts) != self.timestamp

    async def __flush(self):
        while True:
            message = await self.conn.lpop(self.queue_key)
            if not message:
                logging.error('没有旧消息了，退出循环')
                return False
            try:
                await self.on_message(message)
            except Exception as e:
                await self.conn.rpush(self.queue_key, message)
                logging.error(e)
                return True
        # 更新expire
        self.expire(self.queue_key, self.persisted_timeout)
        return False

    async def subscribe(self, timeout=None):
        if timeout:
            self.persisted_timeout = timeout
        if await self.__flush():
            await self.close()
            return
        await self.hash_del()
        logging.error(f'进入订阅:{self.subscribe_chn}')
        chs = await self.conn.subscribe(self.subscribe_chn)
        while True:
            while await chs[0].wait_message():
                msg = await chs[0].get()
                try:
                    await self.on_message(msg)
                    await self.hash_del()
                except Exception as e:
                    await self.conn.unsubscribe(self.subscribe_chn)
                    if await self.duplicate():
                        logging.error('有另外一个实例连接上来了，就不用发了')
                    else:
                        await self.conn.rpush(self.queue_key, msg)
                        await self.expire(self.queue_key, self.persisted_timeout)
                        await self.hash_set(self.queue_key)
                        logging.error('下发通道关闭，向错误队列push')
                    await self.close()
                    return

    async def publish(self, message):
        await self.conn.publish(self.subscribe_chn, message)
        logging.error(f'published to {self.subscribe_chn}!')
        keys = await self.hash_keys()
        logging.error(f'keys:{keys}')
        for key in keys:
            queue_key = await self.hash_get(client_id=key)
            logging.error(f'pub queue:{queue_key}')
            if queue_key:
                await self.conn.rpush(queue_key, message)
                logging.error(f'往失败队列节点{key}push')

