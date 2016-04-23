# -*- coding: utf-8 -*-
'''
The thorium system allows for advanced event tracking and reactions
'''
# Needed:
# Use a top file to load sls files locally
# use the existing state system to compile a low state
# Create a new state runtime to run the low state flow programming style
# Create the thorium plugin system
# Add dynamic recompile of thorium ruleset on given interval

# Import python libs
from __future__ import absolute_import
import os
import time
import logging
import traceback

# Import Salt libs
import salt.state
import salt.payload
from salt.exceptions import SaltRenderError

# TODO: more generic event listener
from salt.netapi.rest_tornado.saltnado import EventListener

import tornado.ioloop

log = logging.getLogger(__name__)


class ThorState(salt.state.HighState):
    '''
    Compile the thorium state and manage it in the thorium runtime
    '''
    def __init__(
            self,
            opts,
            grains=False,
            grain_keys=None,
            pillar=False,
            pillar_keys=None):
        self.ioloop = tornado.ioloop.IOLoop.current()

        self.grains = grains
        self.grain_keys = grain_keys
        self.pillar = pillar
        self.pillar_keys = pillar_keys
        opts['file_roots'] = opts['thorium_roots']
        opts['file_client'] = 'local'
        self.opts = opts
        salt.state.HighState.__init__(self, self.opts, loader='thorium')

        self.event_listener = EventListener(
            {},  # TODO: remove?
            opts,
        )

        self.state._load_states()
        self.state.states.pack.update({
            '__reg__': {},
            '__event_listener__': self.event_listener,
            '__thorium_instances__': {},  # TODO rename
        })


    def start_runtime(self):
        '''
        Start the system!
        '''
        # TODO: deal with changes to sls files
        # call once to set up everything
        self.state.call_chunks(self.get_chunks())

        self.ioloop.start()

    def get_chunks(self, exclude=None, whitelist=None):
        '''
        Compile the top file and return the lowstate for the thorium runtime
        to iterate over
        '''
        ret = {}
        err = []
        try:
            top = self.get_top()
        except SaltRenderError as err:
            return ret
        except Exception:
            trb = traceback.format_exc()
            err.append(trb)
            return err
        err += self.verify_tops(top)
        matches = self.top_matches(top)
        if not matches:
            msg = 'No Top file found!'
            raise SaltRenderError(msg)
        matches = self.matches_whitelist(matches, whitelist)
        high, errors = self.render_highstate(matches)
        if exclude:
            if isinstance(exclude, str):
                exclude = exclude.split(',')
            if '__exclude__' in high:
                high['__exclude__'].extend(exclude)
            else:
                high['__exclude__'] = exclude
            err += errors
        high, ext_errors = self.state.reconcile_extend(high)
        err += ext_errors
        err += self.state.verify_high(high)
        if err:
            raise SaltRenderError(err)
        return self.state.compile_high_data(high)
