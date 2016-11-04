import neovim
import nrepl
import time
import uuid
from pprint import pformat

import re

msleep = lambda x: time.sleep(x/1000.0)

@neovim.plugin
class NreplNvim(object):
    def __init__(self, vim):
        self.__vim = vim
        self.__conn = None
        self.__wc = None

    def __echo(self, data):
        self.__vim.command("echo '[nrepl] {}'".format(pformat(data).replace("'", "\"")))

    def __run(self, operation, callback, timeout = 500):
        if self.__conn == None and self.__auto_connect() == False:
            return

        msgid = uuid.uuid4().hex

        done = False
        def run_callback(msg, wc, key):
            nonlocal done, callback
            done = callback(msg, wc, key)

        self.__wc.watch(msgid, {'id': msgid}, run_callback)
        operation['id'] = msgid
        self.__wc.send(operation)
        for _ in range(timeout):
            if done:
                break
            msleep(1)
        self.__wc.unwatch(msgid)

    def __auto_connect(self):
        port_file = self.__vim.eval("findfile('.nrepl-port', '.;')")
        if port_file == '':
            self.__echo('.nrepl-port is not found')
            return False
        port = open(port_file).read()
        return self.nrepl_connect([port])

    @neovim.command("NreplConnect", nargs=1)
    def nrepl_connect(self, port):
        try:
            self.__conn = nrepl.connect("nrepl://localhost:{}".format(port[0]))
            self.__wc = nrepl.WatchableConnection(self.__conn)
        except ConnectionRefusedError:
            self.__echo('failed to connect %s' % port)
            self.__conn = None
            self.__wc = None
        return self.__conn

    def get_ns_name(self):
        fl = self.__vim.current.buffer[0]
        m = re.search('ns\s([^\s)]+)', fl)
        if m != None:
            return m.group(1)
        return None

    @neovim.autocmd("BufEnter", pattern="*.clj")
    def nrepl_bufenter(self):
        if self.__conn == None:
            return
        fl = self.__vim.current.buffer[0]
        m = re.search('ns\s([^\s)]+)', fl)
        if m != None:
            ns = m.group(1)
            self.nrepl_eval(["(require '{} :reload-all)".format(ns)])
            self.nrepl_eval(["(in-ns '{})".format(ns)])

    @neovim.function("NreplEval", sync=True)
    def nrepl_eval(self, args):
        out = ''
        value = None
        def eval_callback(msg, wc, key):
            nonlocal out, value
            if 'out' in msg:
                out = out + msg['out']
            elif 'value' in msg:
                value = msg['value']
            elif 'status' in msg and msg['status'][0] == 'done':
                return True
            return False

        self.__run({'op': 'eval', 'code': args[0]}, eval_callback)
        return {'out': out, 'value': value}

    # TODO {{{
    #@neovim.function("NreplClone", sync=True)
    #def _clone(self, args):
    #    return True
    #@neovim.function("NreplClose", sync=True)
    #def _close(self):
    #    return True
    #@neovim.function("NreplDescribe", sync=True)
    #def _describe(self):
    #    return True
    #@neovim.function("NreplInterrupt", sync=True)
    #def _interrupt(self):
    #    return True
    #@neovim.function("NreplLoadFile", sync=True)
    #def _load_file(self):
    #    return True
    #@neovim.function("NreplLsSessions", sync=True)
    #def _ls_sessions(self):
    #    return True
    #@neovim.function("NreplStdin", sync=True)
    #def _stdin(self):
    #    return True

    #@neovim.function("ClojureCompletion", sync=True)
    #def completion(self, alias):
    #    op = {"op": "eval", "code": "(map first (ns-publics (get (ns-aliases *ns*) '%s)))" % alias}
    #    return self.run(op)
    # }}}
