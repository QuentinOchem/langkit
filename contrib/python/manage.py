#! /usr/bin/env python
from __future__ import absolute_import, division, print_function

from langkit.libmanage import ManageScript


class Manage(ManageScript):
    def create_context(self, args):
        from langkit.compile_context import CompileCtx

        from language.lexer import python_lexer
        from language.parser import python_grammar

        return CompileCtx(lang_name='python',
                          lexer=python_lexer,
                          grammar=python_grammar)

if __name__ == '__main__':
    Manage().run()
