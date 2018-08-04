import re
import pexpect
import string
from ipykernel.kernelbase import Kernel

class StataKernel(Kernel):
    implementation = 'stata_kernel'
    implementation_version = '0.1'
    language = 'stata'
    language_version = '0.1'
    language_info = {
        'name': 'stata',
        'mimetype': 'text/x-stata',
        'file_extension': '.do',
    }

    def __init__(self, *args, **kwargs):
        super(StataKernel, self).__init__(*args, **kwargs)

        path = '/Applications/Stata/StataSE.app/Contents/MacOS/stata-se'
        self.child = pexpect.spawn(path)
        # Wait/scroll to initial dot prompt
        self.child.expect('\r\n\.')

        # Set banner to Stata's shell header
        banner = self.child.before.decode('utf-8')
        banner = ''.join([x for x in banner if x in string.printable])

        # Remove extra characters before first \r\n
        self.banner = re.sub(r'^.*\r\n', '', banner)

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):

        code = self.remove_comments(code)
        rc, res = self.run_shell(code)
        stream_content = {'text': res}
        if rc:
            stream_content['name'] = 'stderr'
        else:
            stream_content['name'] = 'stdout'

        if not silent:
            self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
               }

    def run_shell(self, code):

        # Split user code into lines
        code = re.sub(r'\r\n', r'\n', code)
        lines = code.split('\n')
        results = []
        for line in lines:
            self.child.sendline(line)
            self.child.expect('\r\n\.')
            res = self.child.before.decode('utf-8')

            # Remove input command, up to first \r\n
            res = re.sub(r'^.+\r\n', '', res)

            # Check error
            err = re.search(r'\r\nr\((\d+)\);', res)
            if err:
                # print(err.group(1), res)
                return err.group(1), res

            results.append(res)

        return '', '\n'.join(results)

    def remove_comments(self, code):
        """Remove block and end-of-line comments from code

        From:


        https://stackoverflow.com/questions/24518020/comprehensive-regexp-to-remove-javascript-comments
        Using the "Final Boss Fight" at the bottom.
        Otherwise it fails on `di 5 / 5 // hello`

        """
        return re.sub(
             r'((["\'])(?:\\[\s\S]|.)*?\2|(?:[^\w\s]|^)\s*\/(?![*\/])(?:\\.|\[(?:\\.|.)\]|.)*?\/(?=[gmiy]{0,4}\s*(?![*\/])(?:\W|$)))|\/\/\/.*?\r?\n\s*|\/\/.*?$|\/\*[\s\S]*?\*\/',
             '\\1', code)

