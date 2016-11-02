import neovim
import nrepl
import pprint

@neovim.plugin
class NreplNvim(object):
    def __init__(self, vim):
        self.__vim = vim
        self.__conn = False

    def __echo(self, data):
        self.__vim.command("echo '[nrepl] {}'".format(pprint.pformat(data).replace("'", "\"")))

    def __run(self, operation):
        result = []
        if self.__conn == False and self.__auto_connect() == False:
            self.__echo('not connected')
            return result

        try:
            self.__conn.write(operation)
        except BrokenPipeError:
            self.__conn = False
            return self.__run(operation)

        while True:
            resp = self.__conn.read()
            result.append(resp)
            if "status" in resp and resp['status'][0] == 'done':
                return result

    def __auto_connect(self):
        port_file = self.__vim.eval("findfile('.nrepl-port', '.;')")
        if port_file == '':
            return False
        port = open(port_file).read()
        return self.nrepl_connect([port])

    @neovim.command("NreplConnect", nargs=1)
    def nrepl_connect(self, port):
        try:
            self.__conn = nrepl.connect("nrepl://localhost:{}".format(port[0]))
        except ConnectionRefusedError:
            self.__echo('failed to connect %s' % port)
            self.__conn = False
        return self.__conn

    @neovim.function("NreplEval", sync=True)
    def nrepl_eval(self, args):
        return self.__run({'op': 'eval', 'code': args[0]})

    # TODO
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
