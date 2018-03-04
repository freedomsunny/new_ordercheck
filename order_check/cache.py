# -*- coding:utf-8 -*-
import redis
import cPickle

from order_check.options import get_options
import order_check.log as logging


auth_opts = [
    {
        "name": "cached_backend",
        "default": 'redis://127.0.0.1:6379/0',
        "help": 'cached backend uri',
        "type": str,
    },
    {
        "name": 'cache_timeout',
        "default": '3600',
        "help": 'cache timeout seconds',
        "type": str,
    }]

options = get_options(auth_opts, 'cache')
LOG = logging.getLogger(__name__)


class Backend(object):
    def __init__(self):
        cached_backend = options.cached_backend
        _conn = cached_backend.split("//")[1]
        if '@' in _conn:
            passwd, host_port = _conn.split('@')
        else:
            passwd = None
            host_port = _conn
        if passwd:
            passwd = passwd[1:]
        host, db_p = host_port.split(':')
        port, db = db_p.split('/')
        self.conn = redis.StrictRedis(host=host, port=port, db=db, password=passwd)

    def get(self, id, default=None):
        """
        Return object with id 
        """
        try:
            ret = self.conn.get(id)
            if ret:
                ret = cPickle.loads(ret)["msg"]
        except:
            ret = default
        return ret

    def set(self, id, user_msg, timeout=options.cache_timeout):
        """
        Set obj into redis-server.
        Expire 3600 sec
        """
        try:
            if user_msg:
                msg = cPickle.dumps({"msg": user_msg})
                self.conn.set(id, msg)
                self.conn.expire(id, timeout)
                return True
        except:
            self.conn.delete(id)
            return False

    def delete(self, id):
        try:
            self.conn.delete(id)
        except:
            pass

    def get_user_roles(self, id):
        cache_id = '%s_%s' % ('roles', id)
        if not self.get(id):
            return []
        roles = self.get(cache_id)
        if not roles:
            if 'roles' in self.get(id):
                roles = [role['name'] for role in self.get(id)['roles']]
                self.set(cache_id, roles)
        return roles

    def keys(self, key):
        return self.conn.keys(key)

    def s_push(self, key, member):
        try:
            self.conn.sadd(key, member)
        except Exception as e:
            LOG.exception("add member <{0}> to <{1}> failed. msg: <{2}>".format(key, member, e))
            return None

    def s_pop(self, key):
        try:
            result = self.conn.spop(key)
            if result:
                return result
            return None
        except Exception as e:
            LOG.exception("pop data <{0}> failed. msg: <{1}>".format(key, e))
            return None

    def l_range(self, key, start, end):
        try:
            if end < start:
                return None
            result = self.conn.lrange(key, start, end)
            if result:
                return result
            return None
        except Exception as e:
            LOG.exception("get member <{0}> failed start: <{1}> end: <{2}> msg: <{2}>".format(key,
                                                                                              start,
                                                                                              end,
                                                                                              e))
            return None
