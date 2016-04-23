# -*- coding: utf-8 -*-
'''
Writes matches to disk to verify activity, helpful when testing
'''

# import python libs
from __future__ import absolute_import
import os
import json

# Import salt libs
import salt.utils

import tornado.gen
import tornado.ioloop
from salt.netapi.rest_tornado.saltnado import Any


class FileSaver(object):
    def __init__(self, name):
        self.name = name
        # TODO: remove
        self._finished = False

        tgt_dir = os.path.join(__opts__['cachedir'], 'thorium', 'saves')
        self.fn_ = os.path.join(tgt_dir, name)
        if not os.path.isdir(tgt_dir):
            os.makedirs(tgt_dir)

        self.wait_events = []
        for req in __low__['require']:
            k, v = req.iteritems().next()
            self.wait_events.append(__thorium_instances__[k][v].event_name)

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.ioloop.spawn_callback(self.save)

    @tornado.gen.coroutine
    def save(self):
        event_futures = []
        for event_name in self.wait_events:
            event_futures.append(__event_listener__.get_event(
                self,
                tag=event_name,
            ))
        while True:
            print 'waiting on', event_futures
            event = yield Any(event_futures)
            with salt.utils.fopen(self.fn_, 'w+') as fp_:
                # TODO: remove hardcoded name
                # TODO: configurable "what to delete??"
                fp_.write(json.dumps(__thorium_instances__['reg'][self.name].values))
            idx = event_futures.index(event)
            event_futures[idx] =  __event_listener__.get_event(
                self,
                tag=self.wait_events[idx],
            )


def save(name):
    '''
    Save the register to <salt cachedir>/thorium/saves/<name>
    '''
    __thorium_instances__['filesaver'] = FileSaver(name)
    # TODO: use this too...
    #__thorium_instances__[name] =  FileSaver(name)
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': True}
    return ret
