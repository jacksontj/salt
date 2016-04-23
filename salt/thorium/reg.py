# -*- coding: utf-8 -*-
'''
Used to manage the thorium register. The thorium register is where compound
values are stored and computed, such as averages etc.
'''

# import python libs
from __future__ import absolute_import, division
import fnmatch

import tornado.ioloop
import tornado.gen

__func_alias__ = {
    'set_': 'set',
    'list_': 'list',
}


# TODO: support multiple types? today, just lists
class Register(object):
    def __init__(self, name, keys, event_glob):
        self.name = name
        self.keys = keys
        self.event_glob = event_glob

        self.values = {}

        # TODO: remove, after async event listener is in salt/utils (instead of importing from saltnado)
        self._finished = False

        # TODO: bootstrap data structure (ping or whatever)

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.ioloop.spawn_callback(self.add)
        #self.ioloop.spawn_callback(self.debug)

    @property
    def event_name(self):
        return 'thorium/reg/{0}/change'.format(self.name)

    @tornado.gen.coroutine
    def debug(self):
        while True:
            print 'Reg {0}: {1}'.format(self.name, self.values)
            yield tornado.gen.sleep(1)

    @tornado.gen.coroutine
    def add(self):
        '''Wait for an event of event_glob and then add it if necessary
        '''
        while True:
            event = yield __event_listener__.get_event(
                self,
                tag=self.event_glob,
            )
            item = {}
            for key in self.keys:
                if key in event['data']:
                    item[key] = event['data'][key]
            if self.name not in self.values:
                self.values[self.name] = []
            self.values[self.name].append(item)

            # TODO make async
            # TODO; not use an event?
            __event_listener__.event.fire_event({}, self.event_name)


def set_(name, add, match):
    '''
    Add a value to the named set
    '''
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': True}
    if name not in __reg__:
        __reg__[name] = {}
        __reg__[name]['val'] = set()
    for event in __events__:
        if fnmatch.fnmatch(event['tag'], match):
            val = event['data'].get(add)
            if val is None:
                val = 'None'
            ret['changes'][add] = val
            __reg__[name]['val'].add(val)
    return ret


def list_(name, add, match):
    '''
    Add to the named list the specified values
    '''
    # TODO: namespae with module name
    if 'reg' not in __thorium_instances__:
        __thorium_instances__['reg'] = {}
    if name in __thorium_instances__['reg']:
        raise Exception('Duplicate thorium named thing!!!')

    __thorium_instances__['reg'][name] =  Register(name, add, match)
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': True,
           }
    return ret


def mean(name, add, match):
    '''
    Accept a numeric value from the matched events and store a running average
    of the values in the given register. If the specified value is not numeric
    it will be skipped
    '''
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': True}
    if name not in __reg__:
        __reg__[name] = {}
        __reg__[name]['val'] = 0
        __reg__[name]['total'] = 0
        __reg__[name]['count'] = 0
    for event in __events__:
        if fnmatch.fnmatch(event['tag'], match):
            if add in event['data']:
                try:
                    comp = int(event['data'])
                except ValueError:
                    continue
            __reg__[name]['total'] += comp
            __reg__[name]['count'] += 1
            __reg__[name]['val'] = __reg__[name]['total'] / __reg__[name]['count']
    return ret
